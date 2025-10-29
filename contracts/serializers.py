from rest_framework import serializers
from .models import ContractTemplate, ContractTemplateVersion, Contract, ContractSignature, ContractTerms, ShareType, ContractShare
from identity.models import Entity
from identity.serializers import EntityListSerializer


class ContractTemplateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    last_contract_number = serializers.SerializerMethodField()

    def get_last_contract_number(self, obj):
        """Get the last contract number for this series."""
        return obj.get_last_contract_number()

    def to_representation(self, instance):
        """
        Convert placeholders to normalized object format for output.
        """
        data = super().to_representation(instance)

        # Normalize placeholders to object format
        placeholders = instance.placeholders or []
        normalized = []

        for placeholder in placeholders:
            if isinstance(placeholder, str):
                # Convert string format to object format
                normalized.append({
                    'key': placeholder,
                    'label': placeholder.replace('_', ' ').replace('.', ' ').title(),
                    'type': 'text',
                    'required': False
                })
            elif isinstance(placeholder, dict):
                # Already in object format, ensure all required fields exist
                normalized.append({
                    'key': placeholder.get('key', ''),
                    'label': placeholder.get('label', placeholder.get('key', '')),
                    'type': placeholder.get('type', 'text'),
                    'required': placeholder.get('required', False)
                })

        data['placeholders'] = normalized
        return data

    class Meta:
        model = ContractTemplate
        fields = [
            'id', 'name', 'description', 'series', 'gdrive_template_file_id',
            'placeholders', 'gdrive_output_folder_id', 'is_active',
            'created_by', 'created_by_email', 'created_at', 'updated_at',
            'last_contract_number'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'last_contract_number']


class ContractTemplateVersionSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = ContractTemplateVersion
        fields = [
            'id', 'template', 'template_name', 'version_number',
            'gdrive_file_id', 'placeholders_snapshot', 'change_description',
            'created_by', 'created_by_email', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']


class ContractSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractSignature
        fields = [
            'id', 'contract', 'signer_email', 'signer_name', 'signer_role',
            'dropbox_sign_signature_id', 'status', 'sent_at', 'viewed_at',
            'signed_at', 'declined_at', 'decline_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['dropbox_sign_signature_id', 'status', 'sent_at', 'viewed_at', 'signed_at', 'declined_at', 'created_at', 'updated_at']


class ShareTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for share types.
    """
    class Meta:
        model = ShareType
        fields = '__all__'


class ContractShareSerializer(serializers.ModelSerializer):
    """
    Serializer for contract shares.
    """
    share_type_name = serializers.CharField(source='share_type.name', read_only=True)
    share_type_code = serializers.CharField(source='share_type.code', read_only=True)
    share_type_code_input = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ContractShare
        fields = [
            'id', 'contract', 'share_type', 'share_type_code', 'share_type_code_input',
            'share_type_name', 'value', 'unit', 'valid_from', 'valid_to',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'share_type': {'required': False}  # Make share_type optional when share_type_code_input is provided
        }

    def validate(self, attrs):
        """Validate that either share_type or share_type_code_input is provided."""
        share_type_code_input = attrs.pop('share_type_code_input', None)

        if share_type_code_input:
            # Resolve share_type_code to share_type ID
            try:
                share_type = ShareType.objects.get(code=share_type_code_input)
                attrs['share_type'] = share_type
            except ShareType.DoesNotExist:
                raise serializers.ValidationError(
                    f"ShareType with code '{share_type_code_input}' not found."
                )
        elif 'share_type' not in attrs:
            raise serializers.ValidationError(
                "Either 'share_type' or 'share_type_code_input' must be provided."
            )

        return attrs


class ContractTermsListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for contract terms in contract list."""
    class Meta:
        model = ContractTerms
        fields = ['contract_duration_years', 'start_date', 'notice_period_days', 'currency']


class ContractSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_version_number = serializers.IntegerField(source='template_version.version_number', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    signatures = ContractSignatureSerializer(many=True, read_only=True)
    shares = ContractShareSerializer(many=True, read_only=True)
    contract_terms = serializers.SerializerMethodField()

    def get_contract_terms(self, obj):
        """Get contract terms for this contract."""
        try:
            terms = ContractTerms.objects.get(contract=obj)
            return ContractTermsListSerializer(terms).data
        except ContractTerms.DoesNotExist:
            return None

    class Meta:
        model = Contract
        fields = [
            'id', 'template', 'template_name', 'template_version', 'template_version_number',
            'contract_number', 'title', 'contract_type', 'department', 'placeholder_values', 'gdrive_file_id',
            'gdrive_file_url', 'gdrive_pdf_file_id', 'gdrive_pdf_file_url',
            'is_public', 'public_share_url', 'status', 'celery_task_id', 'error_message',
            'dropbox_sign_request_id', 'created_by', 'created_by_email', 'created_at',
            'updated_at', 'signed_at', 'signatures', 'shares', 'contract_terms'
        ]
        read_only_fields = ['contract_number', 'gdrive_file_id', 'gdrive_file_url', 'gdrive_pdf_file_id', 'gdrive_pdf_file_url', 'is_public', 'public_share_url', 'celery_task_id', 'error_message', 'dropbox_sign_request_id', 'created_by', 'created_at', 'updated_at', 'signed_at']


class ContractCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a contract from a template.
    """
    template_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    placeholder_values = serializers.JSONField()
    signers = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of signers with 'email', 'name', and 'role'"
    )

    def validate_template_id(self, value):
        try:
            ContractTemplate.objects.get(id=value, is_active=True)
        except ContractTemplate.DoesNotExist:
            raise serializers.ValidationError("Active template not found.")
        return value


class ContractTermsSerializer(serializers.ModelSerializer):
    """
    Serializer for contract terms.
    """
    entity = EntityListSerializer(read_only=True)
    entity_id = serializers.PrimaryKeyRelatedField(
        source='entity',
        queryset=Entity.objects.all(),
        write_only=True
    )
    placeholders = serializers.SerializerMethodField()

    class Meta:
        model = ContractTerms
        fields = [
            'id', 'contract', 'entity', 'entity_id',
            'contract_duration_years', 'notice_period_days',
            'auto_renewal', 'auto_renewal_years',
            'minimum_launches_per_year', 'max_investment_per_song',
            'max_investment_per_year', 'penalty_amount', 'currency',
            'start_date', 'special_terms', 'draft_data',
            'commission_structure',
            'placeholders',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['contract', 'created_by', 'created_at', 'updated_at']

    def get_placeholders(self, obj):
        """Get all placeholders for this contract terms."""
        placeholders = {}

        # Get entity placeholders
        if obj.entity:
            placeholders.update(obj.entity.get_placeholders())

        # Get contract terms placeholders
        placeholders.update(obj.get_placeholders())

        return placeholders


class ContractGenerationSerializer(serializers.Serializer):
    """
    Serializer for contract generation request.
    Combines entity data with contract terms.
    """
    entity_id = serializers.IntegerField()
    template_id = serializers.IntegerField()
    contract_terms = ContractTermsSerializer()

    # Contract shares as nested list
    contract_shares = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of contract shares"
    )

    # Additional placeholder overrides
    placeholder_overrides = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional placeholders or overrides"
    )

    def validate_entity_id(self, value):
        from identity.models import Entity
        try:
            Entity.objects.get(id=value)
        except Entity.DoesNotExist:
            raise serializers.ValidationError("Entity not found.")
        return value

    def validate_template_id(self, value):
        try:
            ContractTemplate.objects.get(id=value, is_active=True)
        except ContractTemplate.DoesNotExist:
            raise serializers.ValidationError("Active template not found.")
        return value

    def create(self, validated_data):
        """
        Create ContractTerms with ContractShares and generate contract.
        """
        entity_id = validated_data.pop('entity_id')
        template_id = validated_data.pop('template_id')
        contract_terms_data = validated_data.pop('contract_terms')
        contract_shares_data = validated_data.pop('contract_shares', [])
        placeholder_overrides = validated_data.pop('placeholder_overrides', {})

        from identity.models import Entity
        entity = Entity.objects.get(id=entity_id)
        template = ContractTemplate.objects.get(id=template_id)

        # Create ContractTerms
        contract_terms = ContractTerms.objects.create(
            entity=entity,
            created_by=self.context['request'].user,
            **contract_terms_data
        )

        # Collect all placeholders
        placeholders = {}
        placeholders.update(entity.get_placeholders())
        placeholders.update(contract_terms.get_placeholders())

        # Add main company (HaHaHa Production) placeholders
        from api.models import CompanySettings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings:
                placeholders.update(company_settings.get_placeholders())
        except CompanySettings.DoesNotExist:
            pass

        # Add today's date placeholders
        from datetime import date
        today = date.today()
        placeholders.update({
            'today.date': today.strftime('%d.%m.%Y'),
            'today.day': str(today.day),
            'today.month': str(today.month),
            'today.year': str(today.year),
        })

        placeholders.update(placeholder_overrides)

        # Create Contract
        from .models import Contract
        contract = Contract.objects.create(
            template=template,
            title=f"Contract - {entity.display_name} - {template.name}",
            placeholder_values=placeholders,
            created_by=self.context['request'].user,
            status='processing',
            counterparty_entity=entity,
            term_start=contract_terms.start_date
        )

        # Link contract to terms
        contract_terms.contract = contract
        contract_terms.save()

        # Create ContractShares
        # Use commission_structure if provided, otherwise use contract_shares_data
        if contract_terms.commission_structure:
            # Expand range-based structure into per-year shares
            expanded_shares = contract_terms.expand_commission_structure()
            for share_data in expanded_shares:
                # Resolve share_type from code
                share_type_code = share_data.pop('share_type_code')
                try:
                    share_type = ShareType.objects.get(code=share_type_code)
                    ContractShare.objects.create(
                        contract=contract,
                        share_type=share_type,
                        **share_data
                    )
                except ShareType.DoesNotExist:
                    # Skip if share type doesn't exist
                    pass
        else:
            # Legacy: use contract_shares_data
            for share_data in contract_shares_data:
                ContractShare.objects.create(
                    contract=contract,
                    **share_data
                )

        # Add share placeholders to contract
        for share in contract.shares.all():
            placeholders.update(share.get_placeholder_values())

        contract.placeholder_values = placeholders
        contract.save()

        # Trigger async generation
        from .tasks import generate_contract_async
        generate_contract_async.delay(contract.id)

        return contract
