from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from django.db import models
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from .models import ContractTemplate, ContractTemplateVersion, Contract, ContractSignature, ContractTerms, ShareType, ContractShare
from .serializers import (
    ContractTemplateSerializer,
    ContractTemplateVersionSerializer,
    ContractSerializer,
    ContractCreateSerializer,
    ContractSignatureSerializer,
    ContractTermsSerializer,
    ShareTypeSerializer,
    ContractShareSerializer,
    ContractGenerationSerializer
)
from .services.contract_generator import ContractGeneratorService
from .services.dropbox_sign import DropboxSignService


class ContractTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contract templates.
    """
    queryset = ContractTemplate.objects.all()
    serializer_class = ContractTemplateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Update template metadata and optionally renumber existing contracts."""
        import logging
        import re

        logger = logging.getLogger(__name__)

        template = self.get_object()
        old_series = template.series

        # Check if series is being changed and if we should update existing contracts
        update_existing = self.request.data.get('update_existing_contracts', False)
        new_series = self.request.data.get('series', old_series)

        # Save the template with new data
        instance = serializer.save()

        # If series changed and update_existing flag is set, renumber all contracts
        if update_existing and new_series != old_series:
            logger.info(f"Renumbering contracts from series '{old_series}' to '{new_series}'")

            contracts = Contract.objects.filter(template=template)
            updated_count = 0

            for contract in contracts:
                # Parse the old contract number
                # Expected format: {old_series}-{number} or {old_series}-{number}bis
                old_number = contract.contract_number

                # Use regex to extract the number part (including bis/ter suffixes)
                pattern = rf'^{re.escape(old_series)}-(.+)$'
                match = re.match(pattern, old_number)

                if match:
                    number_part = match.group(1)  # e.g., "1", "5", "3bis"
                    new_number = f"{new_series}-{number_part}"

                    contract.contract_number = new_number
                    contract.save()
                    updated_count += 1

                    logger.info(f"Updated contract {old_number} → {new_number}")
                else:
                    logger.warning(f"Could not parse contract number: {old_number}")

            logger.info(f"Successfully renumbered {updated_count} contracts")

        return instance

    def destroy(self, request, *args, **kwargs):
        """
        Delete a template. Only allowed if no contracts have been generated from it.
        """
        template = self.get_object()

        # Check if any contracts exist for this template
        if template.contracts.exists():
            return Response(
                {
                    'error': 'Cannot delete template with existing contracts',
                    'contracts_count': template.contracts.count()
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        Create a new version of the template.
        """
        template = self.get_object()

        # Get the latest version number
        latest_version = template.versions.first()
        new_version_number = (latest_version.version_number + 1) if latest_version else 1

        # Create new version
        version = ContractTemplateVersion.objects.create(
            template=template,
            version_number=new_version_number,
            gdrive_file_id=request.data.get('gdrive_file_id', template.gdrive_template_file_id),
            placeholders_snapshot=request.data.get('placeholders', template.placeholders),
            change_description=request.data.get('change_description', ''),
            created_by=request.user
        )

        # Update template if needed
        if request.data.get('update_template', False):
            template.gdrive_template_file_id = version.gdrive_file_id
            template.placeholders = version.placeholders_snapshot
            template.save()

        serializer = ContractTemplateVersionSerializer(version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Get all versions of the template.
        """
        template = self.get_object()
        versions = template.versions.all()
        serializer = ContractTemplateVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def import_from_drive(self, request):
        """
        Import a template from Google Drive.
        User selects a file from Google Drive and adds it as a template.
        """
        gdrive_file_id = request.data.get('gdrive_file_id')
        name = request.data.get('name')
        description = request.data.get('description', '')
        placeholders = request.data.get('placeholders', [])
        gdrive_output_folder_id = request.data.get('gdrive_output_folder_id')

        if not gdrive_file_id or not name or not gdrive_output_folder_id:
            return Response(
                {'error': 'gdrive_file_id, name, and gdrive_output_folder_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify file exists in Google Drive
            from .services.google_drive import GoogleDriveService
            drive_service = GoogleDriveService()
            file_info = drive_service.get_file(gdrive_file_id)

            # Create template record
            template = ContractTemplate.objects.create(
                name=name,
                description=description,
                gdrive_template_file_id=gdrive_file_id,
                placeholders=placeholders,
                gdrive_output_folder_id=gdrive_output_folder_id,
                created_by=request.user
            )

            serializer = ContractTemplateSerializer(template)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Failed to import template: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search_drive_documents(self, request):
        """
        Search for Google Docs documents in Drive.
        """
        query = request.query_params.get('query', '')
        limit = int(request.query_params.get('limit', 20))

        try:
            from .services.google_drive import GoogleDriveService
            drive_service = GoogleDriveService()
            documents = drive_service.search_documents(query=query, limit=limit)
            return Response({'documents': documents})
        except Exception as e:
            return Response(
                {'error': f'Failed to search documents: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search_drive_folders(self, request):
        """
        Search for folders in Drive.
        """
        query = request.query_params.get('query', '')
        limit = int(request.query_params.get('limit', 20))

        try:
            from .services.google_drive import GoogleDriveService
            drive_service = GoogleDriveService()
            folders = drive_service.search_folders(query=query, limit=limit)
            return Response({'folders': folders})
        except Exception as e:
            return Response(
                {'error': f'Failed to search folders: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from .rbac import ContractsRBAC, ContractTypePolicy
from .permissions import CanMakePublic, CanSendForSignature


class ContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contracts.
    """
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by template
        template_id = self.request.query_params.get('template')
        if template_id:
            queryset = queryset.filter(template_id=template_id)

        # Filter by counterparty entity
        entity_id = self.request.query_params.get('counterparty_entity')
        if entity_id:
            queryset = queryset.filter(counterparty_entity_id=entity_id)

        # RBAC scoping: non-admins only see their department and allowed types
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            prof = getattr(user, 'profile', None)
            is_admin = getattr(user, 'is_superuser', False) or (prof and prof.role == 'administrator')
            if not is_admin and prof and prof.department:
                try:
                    # Get allowed types for view
                    allowed_types = ContractTypePolicy.objects.filter(
                        role=prof.role,
                        department=prof.department,
                        can_view=True,
                    ).values_list('contract_type', flat=True)
                    queryset = queryset.filter(
                        models.Q(department__isnull=True) | models.Q(department=prof.department),
                        models.Q(contract_type__isnull=True) | models.Q(contract_type__in=list(allowed_types))
                    )
                except Exception:
                    # Fallback if policy table not available: only department scoping
                    queryset = queryset.filter(
                        models.Q(department__isnull=True) | models.Q(department=prof.department)
                    )
        return queryset

    def update(self, request, *args, **kwargs):
        """
        Update contract details (title, status, placeholder_values).
        Cannot update if contract is already signed.
        """
        contract = self.get_object()

        # RBAC: require can_update unless admin
        user = request.user
        prof = getattr(user, 'profile', None)
        is_admin = getattr(user, 'is_superuser', False) or (prof and prof.role == 'administrator')
        if not is_admin and not ContractsRBAC(user).can_update(contract):
            return Response({'error': 'Not allowed to update this contract'}, status=status.HTTP_403_FORBIDDEN)

        if contract.status == 'signed':
            return Response(
                {'error': 'Cannot update a signed contract'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Allow updating title, status, and placeholder_values for drafts
        allowed_fields = ['title', 'placeholder_values']
        if contract.status in ['draft', 'pending_signature']:
            allowed_fields.append('status')

        # Filter request data to only allowed fields
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = self.get_serializer(contract, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests."""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a contract. Cannot delete signed contracts.
        """
        contract = self.get_object()

        # RBAC: require can_delete unless admin
        user = request.user
        prof = getattr(user, 'profile', None)
        is_admin = getattr(user, 'is_superuser', False) or (prof and prof.role == 'administrator')
        if not is_admin and not ContractsRBAC(user).can_delete(contract):
            return Response({'error': 'Not allowed to delete this contract'}, status=status.HTTP_403_FORBIDDEN)

        if contract.status == 'signed':
            return Response(
                {'error': 'Cannot delete a signed contract'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If contract has a Dropbox Sign request, try to cancel it
        if contract.dropbox_sign_request_id:
            try:
                from .services.dropbox_sign import DropboxSignService
                dropbox_service = DropboxSignService()
                dropbox_service.cancel_signature_request(contract.dropbox_sign_request_id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not cancel signature request: {str(e)}")

        # Delete the contract
        contract.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate a new contract from a template (async).
        Returns immediately with status='processing'.
        """
        import logging
        from .tasks import generate_contract_async

        logger = logging.getLogger(__name__)

        serializer = ContractCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template_id = serializer.validated_data['template_id']
        title = serializer.validated_data['title']
        placeholder_values = serializer.validated_data['placeholder_values']

        logger.info(f"Generating contract from template {template_id}")
        logger.info(f"Placeholder values received: {placeholder_values}")

        template = ContractTemplate.objects.get(id=template_id)
        logger.info(f"Template placeholders defined: {template.placeholders}")

        # Add company placeholders automatically
        from api.models import CompanySettings
        company_settings = CompanySettings.load()
        company_placeholders = company_settings.get_placeholders()

        # Merge company placeholders with user-provided placeholders
        # User placeholders take precedence
        all_placeholders = {}
        all_placeholders.update(company_placeholders)
        all_placeholders.update(placeholder_values)

        logger.info(f"Total placeholders: {len(all_placeholders)} (company: {len(company_placeholders)}, user: {len(placeholder_values)})")

        # Generate contract number using template series
        # Allow manual override via request data (for "bis" variants)
        contract_number = request.data.get('contract_number')
        if not contract_number:
            contract_number = template.get_next_contract_number()

        logger.info(f"Generated contract number: {contract_number}")

        # Create contract record with status='processing'
        contract = Contract.objects.create(
            template=template,
            contract_number=contract_number,
            title=title,
            placeholder_values=all_placeholders,
            status='processing',
            created_by=request.user,
            department=getattr(getattr(request.user, 'profile', None), 'department', None),
        )

        # Start async task
        task = generate_contract_async.delay(contract.id)

        # Save task ID
        contract.celery_task_id = task.id
        contract.save()

        logger.info(f"Started async generation for contract {contract.id}, task {task.id}")

        # Return immediately with processing status
        response_serializer = ContractSerializer(contract)
        return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """
        Regenerate a contract with updated placeholder values (async).
        Only allowed for draft contracts.
        Returns immediately with status='processing'.
        """
        import logging
        from .tasks import regenerate_contract_async

        logger = logging.getLogger(__name__)

        contract = self.get_object()

        # RBAC: require can_regenerate unless admin
        user = request.user
        prof = getattr(user, 'profile', None)
        is_admin = getattr(user, 'is_superuser', False) or (prof and prof.role == 'administrator')
        if not is_admin and not ContractsRBAC(user).can_regenerate(contract):
            return Response({'error': 'Not allowed to regenerate this contract'}, status=status.HTTP_403_FORBIDDEN)

        if contract.status not in ['draft', 'failed']:
            return Response(
                {'error': 'Can only regenerate draft or failed contracts'},
                status=status.HTTP_400_BAD_REQUEST
            )

        placeholder_values = request.data.get('placeholder_values')
        if not placeholder_values:
            return Response(
                {'error': 'placeholder_values is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Regenerating contract {contract.id}")
        logger.info(f"New placeholder values: {placeholder_values}")

        # Start async task
        task = regenerate_contract_async.delay(contract.id, placeholder_values)

        # Update contract status and task ID
        contract.celery_task_id = task.id
        contract.status = 'processing'
        contract.error_message = ''
        contract.save()

        logger.info(f"Started async regeneration for contract {contract.id}, task {task.id}")

        # Return immediately with processing status
        serializer = ContractSerializer(contract)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        """
        Check the status of contract generation/regeneration.
        Returns current contract status.
        """
        contract = self.get_object()
        serializer = ContractSerializer(contract)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanMakePublic])
    def make_public(self, request, pk=None):
        """
        Make a contract publicly accessible.
        """
        contract = self.get_object()

        if not contract.gdrive_file_id:
            return Response(
                {'error': 'Contract must have a Google Drive file'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if contract.is_public:
            return Response(
                {'message': 'Contract is already public', 'public_url': contract.public_share_url}
            )

        try:
            from .services.google_drive import GoogleDriveService
            drive_service = GoogleDriveService()
            public_url = drive_service.make_file_public(contract.gdrive_file_id)

            contract.is_public = True
            contract.public_share_url = public_url
            contract.save()

            serializer = ContractSerializer(contract)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': f'Failed to make contract public: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanSendForSignature])
    def send_for_signature(self, request, pk=None):
        """
        Send contract for signature via Dropbox Sign (async).
        Generates PDF if it doesn't exist yet.
        Returns immediately with status='processing'.
        """
        import logging
        from .tasks import send_for_signature_async

        logger = logging.getLogger(__name__)

        contract = self.get_object()

        if not contract.gdrive_file_id:
            return Response(
                {'error': 'Contract must be generated first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        signers_data = request.data.get('signers', [])
        if not signers_data:
            return Response(
                {'error': 'At least one signer is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        test_mode = request.data.get('test_mode', True)

        logger.info(f"Sending contract {contract.id} for signature (async)")

        # Start async task
        task = send_for_signature_async.delay(contract.id, signers_data, test_mode)

        # Update contract status and task ID
        contract.celery_task_id = task.id
        contract.status = 'processing'
        contract.error_message = ''
        contract.save()

        logger.info(f"Started async signature sending for contract {contract.id}, task {task.id}")

        # Return immediately with processing status
        serializer = ContractSerializer(contract)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def signature_status(self, request, pk=None):
        """
        Get signature status from Dropbox Sign and sync to database.
        """
        import logging
        logger = logging.getLogger(__name__)

        contract = self.get_object()

        if not contract.dropbox_sign_request_id:
            return Response(
                {'error': 'Contract has not been sent for signature'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dropbox_service = DropboxSignService()
            signature_request = dropbox_service.get_signature_request(
                contract.dropbox_sign_request_id
            )

            logger.info(f"Syncing signature status for contract {contract.id}")

            # Sync signature statuses to database
            for sig in signature_request.signatures:
                try:
                    # Find matching signature by email
                    db_signature = ContractSignature.objects.filter(
                        contract=contract,
                        signer_email=sig.signer_email_address
                    ).first()

                    if db_signature:
                        # Map Dropbox Sign status to our status
                        status_code = sig.status_code if hasattr(sig, 'status_code') else None

                        if status_code == 'signed':
                            db_signature.status = 'signed'
                            if hasattr(sig, 'signed_at') and sig.signed_at:
                                db_signature.signed_at = timezone.datetime.fromtimestamp(sig.signed_at, tz=timezone.utc)
                        elif status_code == 'declined':
                            db_signature.status = 'declined'
                            if hasattr(sig, 'declined_at') and sig.declined_at:
                                db_signature.declined_at = timezone.datetime.fromtimestamp(sig.declined_at, tz=timezone.utc)

                        # Update viewed timestamp
                        if hasattr(sig, 'last_viewed_at') and sig.last_viewed_at:
                            db_signature.viewed_at = timezone.datetime.fromtimestamp(sig.last_viewed_at, tz=timezone.utc)

                        # Update signature ID
                        if hasattr(sig, 'signature_id'):
                            db_signature.dropbox_sign_signature_id = sig.signature_id

                        db_signature.save()
                        logger.info(f"Updated signature for {sig.signer_email_address}: {status_code}")

                except Exception as e:
                    logger.warning(f"Failed to update signature for {sig.signer_email_address}: {str(e)}")

            # Check if contract should be marked as signed
            if signature_request.is_complete and contract.status != 'signed':
                logger.info(f"Marking contract {contract.id} as signed (all signatures complete)")
                contract.status = 'signed'
                contract.signed_at = timezone.now()
                contract.save()

                # Update all signatures to signed if not already
                contract.signatures.filter(status='pending').update(
                    status='signed',
                    signed_at=timezone.now()
                )

            # Refresh contract from database
            contract.refresh_from_db()
            serializer = ContractSerializer(contract)

            return Response({
                'signature_request_id': signature_request.signature_request_id,
                'is_complete': signature_request.is_complete,
                'has_error': signature_request.has_error,
                'signatures': signature_request.signatures,
                'contract': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to get signature status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate_with_terms(self, request):
        """
        Generate a contract with entity and contract terms.
        This endpoint handles the full contract generation with all business terms.
        """
        import logging
        from .tasks import generate_contract_async
        from identity.models import Entity

        logger = logging.getLogger(__name__)

        # Use ContractGenerationSerializer to validate the data
        serializer = ContractGenerationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Extract validated data
        entity_id = serializer.validated_data['entity_id']
        template_id = serializer.validated_data['template_id']
        contract_terms_data = serializer.validated_data.get('contract_terms', {})
        contract_shares_data = serializer.validated_data.get('contract_shares', [])
        placeholder_overrides = serializer.validated_data.get('placeholder_overrides', {})

        logger.info(f"Generating contract with terms for entity {entity_id}, template {template_id}")

        entity = Entity.objects.get(id=entity_id)
        template = ContractTemplate.objects.get(id=template_id)

        # Remove entity from contract_terms_data if it exists (to avoid duplicate)
        contract_terms_data.pop('entity', None)
        contract_terms_data.pop('entity_id', None)

        # Generate contract number using template series
        # Allow manual override via request data (for "bis" variants)
        contract_number = request.data.get('contract_number')
        if not contract_number:
            contract_number = template.get_next_contract_number()

        logger.info(f"Generated contract number: {contract_number}")

        # Create Contract first
        contract = Contract.objects.create(
            template=template,
            contract_number=contract_number,
            title=f"Contract - {entity.display_name} - {template.name}",
            counterparty_entity=entity,
            placeholder_values={},  # Will be updated after creating shares
            status='processing',
            created_by=request.user,
            department=getattr(getattr(request.user, 'profile', None), 'department', None),
        )

        # Create ContractTerms linked to contract
        contract_terms = ContractTerms.objects.create(
            contract=contract,
            entity=entity,
            created_by=request.user,
            **contract_terms_data
        )

        # Create ContractShares using serializer for proper validation
        for share_data in contract_shares_data:
            share_serializer = ContractShareSerializer(data={
                'contract': contract.id,
                **share_data
            })
            share_serializer.is_valid(raise_exception=True)
            share_serializer.save()

        # Collect all placeholders
        from api.models import CompanySettings

        placeholders = {}

        # Add company placeholders (first party)
        company_settings = CompanySettings.load()
        placeholders.update(company_settings.get_placeholders())

        # Add entity placeholders (second party - artist/counterparty)
        placeholders.update(entity.get_placeholders())

        # Add contract terms placeholders
        placeholders.update(contract_terms.get_placeholders())

        # Get share placeholders
        for share in contract.shares.all():
            placeholders.update(share.get_placeholder_values())

        # Apply manual overrides last
        placeholders.update(placeholder_overrides)

        logger.info(f"Collected {len(placeholders)} placeholders for contract generation")
        logger.info(f"Placeholder keys: {list(placeholders.keys())}")

        # Update contract with placeholders
        contract.placeholder_values = placeholders
        contract.save()

        # Start async generation task
        task = generate_contract_async.delay(contract.id)
        contract.celery_task_id = task.id
        contract.save()

        logger.info(f"Started async generation for contract {contract.id}, task {task.id}")

        # Return contract with terms
        response_data = ContractSerializer(contract).data
        response_data['contract_terms'] = ContractTermsSerializer(contract_terms).data

        return Response(response_data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'])
    def preview_generation(self, request):
        """
        Preview contract generation by collecting all placeholders.
        Does not create the actual contract, just returns what would be generated.
        """
        from identity.models import Entity

        # Validate data
        entity_id = request.data.get('entity_id')
        template_id = request.data.get('template_id')
        contract_terms_data = request.data.get('contract_terms', {})
        commission_schedules_data = request.data.get('commission_schedules', [])
        placeholder_overrides = request.data.get('placeholder_overrides', {})

        if not entity_id or not template_id:
            return Response(
                {'error': 'entity_id and template_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entity = Entity.objects.get(id=entity_id)
            template = ContractTemplate.objects.get(id=template_id)
        except Entity.DoesNotExist:
            return Response({'error': 'Entity not found'}, status=status.HTTP_404_NOT_FOUND)
        except ContractTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=status.HTTP_404_NOT_FOUND)

        # Create temporary ContractTerms for preview (not saved)
        contract_terms = ContractTerms(
            entity=entity,
            **contract_terms_data
        )

        # Collect placeholders
        placeholders = {}
        placeholders.update(entity.get_placeholders())
        placeholders.update(contract_terms.get_placeholders())

        # Process commission schedules
        for schedule_data in commission_schedules_data:
            temp_schedule = CommissionSchedule(**schedule_data)
            placeholders.update(temp_schedule.get_placeholders())

        placeholders.update(placeholder_overrides)

        # Return preview data
        return Response({
            'entity': {
                'id': entity.id,
                'display_name': entity.display_name,
                'kind': entity.kind
            },
            'template': {
                'id': template.id,
                'name': template.name,
                'placeholders': template.placeholders
            },
            'placeholders': placeholders,
            'placeholder_count': len(placeholders),
            'missing_placeholders': [
                p for p in template.placeholders
                if p not in placeholders or not placeholders[p]
            ]
        })

    @action(detail=False, methods=['get'])
    def template_placeholders(self, request):
        """
        Get all available placeholders for a template and entity type.
        This helps the frontend know what fields to show.
        """
        template_id = request.query_params.get('template_id')
        entity_kind = request.query_params.get('entity_kind', 'PF')

        if not template_id:
            return Response(
                {'error': 'template_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            template = ContractTemplate.objects.get(id=template_id)
        except ContractTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get example placeholders based on entity type
        placeholders = {
            'template': template.placeholders,
            'entity': [],
            'contract_terms': [],
            'commission': []
        }

        # Entity placeholders
        if entity_kind == 'PF':
            placeholders['entity'] = [
                'person.full_name', 'person.first_name', 'person.last_name',
                'artist.stage_name', 'person.nationality', 'person.email',
                'person.phone', 'person.shares', 'person.address',
                'person.city', 'person.state', 'person.zip_code',
                'person.country', 'bank.iban', 'bank.name', 'bank.branch',
                'id.cnp', 'id.series', 'id.number', 'id.issued_by',
                'id.issued_date', 'id.expiry_date', 'person.birth_date',
                'person.birth_place'
            ]
        else:  # PJ
            placeholders['entity'] = [
                'company.name', 'company.registration_number', 'company.vat_number',
                'company.address', 'company.city', 'company.state',
                'company.zip_code', 'company.country', 'company.email',
                'company.phone', 'bank.iban', 'bank.name', 'bank.branch'
            ]

        # Contract terms placeholders
        placeholders['contract_terms'] = [
            'contract.duration_years', 'contract.notice_period_days',
            'contract.auto_renewal', 'contract.auto_renewal_years',
            'contract.minimum_launches_per_year', 'contract.max_investment_per_song',
            'contract.max_investment_per_year', 'contract.penalty_amount',
            'contract.currency', 'contract.start_date', 'contract.end_date',
            'contract.special_terms'
        ]

        # Commission placeholders (year-based)
        placeholders['commission'] = [
            'commission.year1.concert', 'commission.year1.rights',
            'commission.year1.merchandising', 'commission.year1.image_rights',
            'commission.year1.ppd', 'commission.year1.emd', 'commission.year1.sync',
            'commission.year2.concert', 'commission.year2.rights',
            # ... etc for other years
        ]

        return Response(placeholders)

    @action(detail=False, methods=['post'])
    def save_draft(self, request):
        """
        Save draft contract terms for later use.
        This allows users to save their progress without generating the contract.
        """
        from identity.models import Entity

        entity_id = request.data.get('entity_id')
        draft_data = request.data.get('draft_data', {})

        if not entity_id:
            return Response(
                {'error': 'entity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({'error': 'Entity not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if contract terms already exist for this entity
        contract_terms, created = ContractTerms.objects.get_or_create(
            entity=entity,
            contract__isnull=True,  # Only get terms not yet linked to a contract
            defaults={'created_by': request.user}
        )

        # Update draft data
        contract_terms.draft_data = draft_data
        contract_terms.save()

        return Response({
            'message': 'Draft saved successfully',
            'contract_terms_id': contract_terms.id,
            'created': created
        })

    @action(detail=False, methods=['get'])
    def load_draft(self, request):
        """
        Load saved draft contract terms for an entity.
        """
        from identity.models import Entity

        entity_id = request.query_params.get('entity_id')

        if not entity_id:
            return Response(
                {'error': 'entity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            return Response({'error': 'Entity not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get the latest unlinked contract terms
        contract_terms = ContractTerms.objects.filter(
            entity=entity,
            contract__isnull=True
        ).first()

        if not contract_terms:
            return Response({'message': 'No draft found', 'draft_data': None})

        serializer = ContractTermsSerializer(contract_terms)
        return Response({
            'message': 'Draft loaded successfully',
            'contract_terms': serializer.data,
            'draft_data': contract_terms.draft_data
        })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def dropbox_sign_webhook(request):
    """
    Webhook endpoint for Dropbox Sign callbacks.

    This endpoint receives events from Dropbox Sign when signature status changes.
    No authentication required - webhooks are verified using the event hash.

    Configure this URL in your Dropbox Sign account settings:
    https://your-domain.com/api/v1/contracts/webhook/dropbox-sign/
    """
    import logging
    import json
    from dropbox_sign import EventCallbackRequest, EventCallbackHelper
    from decouple import config

    logger = logging.getLogger(__name__)

    try:
        # Get API key from settings
        api_key = config('DROPBOX_SIGN_API_KEY')

        # Parse callback data - Dropbox Sign sends JSON in a form parameter called "json"
        if request.POST and 'json' in request.POST:
            # Form-encoded JSON (most common from Dropbox Sign)
            callback_data = json.loads(request.POST['json'])
        elif hasattr(request, 'data') and request.data:
            # DRF parsed data
            callback_data = request.data
        elif request.body:
            # Raw JSON body
            try:
                callback_data = json.loads(request.body.decode('utf-8'))
            except:
                callback_data = {}
        else:
            callback_data = {}

        logger.info(f"Received Dropbox Sign webhook")
        logger.debug(f"Callback data type: {type(callback_data)}")
        logger.debug(f"Callback data: {callback_data}")

        # Check if it's a test ping or empty callback
        if not callback_data or 'event' not in callback_data:
            logger.info("Received test ping or empty callback from Dropbox Sign")
            return HttpResponse("Hello API Event Received", status=200)

        # Initialize event callback
        try:
            callback_event = EventCallbackRequest.init(callback_data)
        except Exception as e:
            logger.error(f"Failed to parse callback event: {str(e)}")
            logger.error(f"Raw callback data: {callback_data}")
            return HttpResponse("Hello API Event Received", status=200)

        # Verify callback authenticity
        try:
            if not EventCallbackHelper.is_valid(api_key, callback_event):
                logger.warning("Invalid Dropbox Sign webhook - signature verification failed")
                return HttpResponse("Invalid signature", status=400)
        except Exception as e:
            logger.warning(f"Signature verification failed: {str(e)}")
            # Continue anyway for testing - remove this in production
            pass

        # Get event details
        event = callback_event.event
        if not event:
            logger.warning("No event in callback")
            return HttpResponse("Hello API Event Received", status=200)

        event_type = event.event_type

        logger.info(f"Processing Dropbox Sign event: {event_type}")

        # Get signature request data
        signature_request = callback_event.signature_request
        if not signature_request:
            logger.warning("No signature request in callback")
            return HttpResponse("Hello API Event Received", status=200)

        signature_request_id = signature_request.signature_request_id

        # Find contract by signature request ID
        try:
            contract = Contract.objects.get(dropbox_sign_request_id=signature_request_id)
        except Contract.DoesNotExist:
            logger.warning(f"Contract not found for signature request: {signature_request_id}")
            return HttpResponse("Hello API Event Received", status=200)

        # Update contract based on event type
        if event_type == 'signature_request_all_signed':
            logger.info(f"Contract {contract.id} fully signed")
            contract.status = 'signed'
            contract.signed_at = timezone.now()
            contract.save()

            # Update all signatures to signed
            contract.signatures.all().update(
                status='signed',
                signed_at=timezone.now()
            )

        elif event_type == 'signature_request_signed':
            logger.info(f"Signature received for contract {contract.id}")

            # Update specific signer
            if event.event_metadata and hasattr(event.event_metadata, 'related_signature_id'):
                related_signature_id = event.event_metadata.related_signature_id

                # Find matching signature in our records by email
                for sig in signature_request.signatures:
                    if hasattr(sig, 'signature_id') and sig.signature_id == related_signature_id:
                        ContractSignature.objects.filter(
                            contract=contract,
                            signer_email=sig.signer_email_address
                        ).update(
                            status='signed',
                            signed_at=timezone.now(),
                            dropbox_sign_signature_id=sig.signature_id
                        )
                        break

            # Check if all signers have signed
            total_signers = contract.signatures.count()
            signed_count = contract.signatures.filter(status='signed').count()

            logger.info(f"Contract {contract.id}: {signed_count}/{total_signers} signers have signed")

            if total_signers > 0 and signed_count == total_signers:
                logger.info(f"All signers complete! Marking contract {contract.id} as signed")
                contract.status = 'signed'
                contract.signed_at = timezone.now()
                contract.save()

        elif event_type == 'signature_request_viewed':
            logger.info(f"Contract {contract.id} viewed by signer")

            # Update specific signer viewed status
            if event.event_metadata and hasattr(event.event_metadata, 'related_signature_id'):
                related_signature_id = event.event_metadata.related_signature_id

                for sig in signature_request.signatures:
                    if hasattr(sig, 'signature_id') and sig.signature_id == related_signature_id:
                        ContractSignature.objects.filter(
                            contract=contract,
                            signer_email=sig.signer_email_address
                        ).update(
                            viewed_at=timezone.now(),
                            dropbox_sign_signature_id=sig.signature_id
                        )
                        break

        elif event_type == 'signature_request_declined':
            logger.info(f"Contract {contract.id} declined by signer")
            contract.status = 'cancelled'
            contract.save()

            # Update specific signer
            if event.event_metadata and hasattr(event.event_metadata, 'related_signature_id'):
                related_signature_id = event.event_metadata.related_signature_id

                for sig in signature_request.signatures:
                    if hasattr(sig, 'signature_id') and sig.signature_id == related_signature_id:
                        ContractSignature.objects.filter(
                            contract=contract,
                            signer_email=sig.signer_email_address
                        ).update(
                            status='declined',
                            declined_at=timezone.now(),
                            dropbox_sign_signature_id=sig.signature_id
                        )
                        break

        elif event_type == 'signature_request_sent':
            logger.info(f"Contract {contract.id} signature request sent")
            # Already handled in send_for_signature

        else:
            logger.info(f"Unhandled event type: {event_type}")

        # Return success response (required by Dropbox Sign)
        return HttpResponse("Hello API Event Received", status=200)

    except Exception as e:
        logger.error(f"Error processing Dropbox Sign webhook: {str(e)}")
        logger.exception(e)
        return HttpResponse("Error processing webhook", status=500)
