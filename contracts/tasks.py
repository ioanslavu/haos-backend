"""
Celery tasks for async contract processing.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='contracts.generate_contract_async')
def generate_contract_async(self, contract_id):
    """
    Async task to generate contract in Google Drive.

    Args:
        contract_id: ID of the contract to generate

    Returns:
        dict: Result with success status and contract_id (sensitive data saved to database)
    """
    from .models import Contract
    from .services.contract_generator import ContractGeneratorService

    try:
        logger.info(f"Starting async contract generation for contract {contract_id}")

        # Get contract
        contract = Contract.objects.get(id=contract_id)

        # Generate contract in Google Drive
        generator = ContractGeneratorService()
        result = generator.generate_contract(
            template_file_id=contract.template.gdrive_template_file_id,
            output_folder_id=contract.template.gdrive_output_folder_id,
            output_file_name=f"{contract.contract_number}_{contract.title}",
            placeholder_values=contract.placeholder_values
        )

        # Update contract with Google Drive info
        contract.gdrive_file_id = result['file_id']
        contract.gdrive_file_url = result['web_view_link']
        contract.status = 'draft'
        contract.error_message = ''
        contract.save()

        logger.info(f"Successfully generated contract {contract_id}")

        # Return minimal data - frontend fetches full contract from database
        return {
            'success': True,
            'contract_id': contract_id
        }

    except Contract.DoesNotExist:
        error_msg = f"Contract {contract_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

    except Exception as e:
        error_msg = f"Failed to generate contract: {str(e)}"
        logger.error(f"Error generating contract {contract_id}: {error_msg}")

        # Update contract with error status
        try:
            contract = Contract.objects.get(id=contract_id)
            contract.status = 'failed'
            contract.error_message = error_msg
            contract.save()
        except Exception as save_error:
            logger.error(f"Failed to update contract status: {str(save_error)}")

        return {'success': False, 'error': error_msg}


@shared_task(bind=True, name='contracts.regenerate_contract_async')
def regenerate_contract_async(self, contract_id, placeholder_values):
    """
    Async task to regenerate contract with new placeholder values.

    Args:
        contract_id: ID of the contract to regenerate
        placeholder_values: New placeholder values dict

    Returns:
        dict: Result with success status and contract_id (sensitive data saved to database)
    """
    from .models import Contract
    from .services.contract_generator import ContractGeneratorService

    try:
        logger.info(f"Starting async contract regeneration for contract {contract_id}")

        # Get contract
        contract = Contract.objects.get(id=contract_id)

        # Update status to processing
        contract.status = 'processing'
        contract.save()

        # Generate new contract file in Google Drive
        generator = ContractGeneratorService()
        result = generator.generate_contract(
            template_file_id=contract.template.gdrive_template_file_id,
            output_folder_id=contract.template.gdrive_output_folder_id,
            output_file_name=f"{contract.contract_number}_{contract.title}",
            placeholder_values=placeholder_values
        )

        # Update contract with new Google Drive info
        contract.gdrive_file_id = result['file_id']
        contract.gdrive_file_url = result['web_view_link']
        contract.placeholder_values = placeholder_values
        contract.status = 'draft'
        contract.error_message = ''
        contract.save()

        logger.info(f"Successfully regenerated contract {contract_id}")

        # Return minimal data - frontend fetches full contract from database
        return {
            'success': True,
            'contract_id': contract_id
        }

    except Contract.DoesNotExist:
        error_msg = f"Contract {contract_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

    except Exception as e:
        error_msg = f"Failed to regenerate contract: {str(e)}"
        logger.error(f"Error regenerating contract {contract_id}: {error_msg}")

        # Update contract with error status
        try:
            contract = Contract.objects.get(id=contract_id)
            contract.status = 'failed'
            contract.error_message = error_msg
            contract.save()
        except Exception as save_error:
            logger.error(f"Failed to update contract status: {str(save_error)}")

        return {'success': False, 'error': error_msg}


@shared_task(bind=True, name='contracts.send_for_signature_async')
def send_for_signature_async(self, contract_id, signers_data, test_mode=True):
    """
    Async task to send contract for signature via Dropbox Sign.
    Generates PDF if needed, makes it public, and sends signature request.

    Args:
        contract_id: ID of the contract to send
        signers_data: List of signer dicts with email, name, role
        test_mode: Whether to use Dropbox Sign test mode

    Returns:
        dict: Result with success status and contract_id (sensitive data saved to database)
    """
    from .models import Contract, ContractSignature
    from .services.contract_generator import ContractGeneratorService
    from .services.google_drive import GoogleDriveService
    from .services.dropbox_sign import DropboxSignService

    try:
        logger.info(f"Starting async signature sending for contract {contract_id}")

        # Get contract
        contract = Contract.objects.get(id=contract_id)

        # Generate PDF if it doesn't exist
        if not contract.gdrive_pdf_file_id:
            logger.info(f"Generating PDF for contract {contract_id}")

            generator = ContractGeneratorService()
            drive_service = GoogleDriveService()

            # Export Google Docs as PDF
            pdf_content = generator.export_as_pdf(contract.gdrive_file_id)

            # Upload PDF to Google Drive
            pdf_result = drive_service.upload_file_content(
                content=pdf_content,
                file_name=f"{contract.contract_number}_{contract.title}.pdf",
                folder_id=contract.template.gdrive_output_folder_id,
                mime_type='application/pdf'
            )

            # Make PDF publicly accessible for Dropbox Sign
            pdf_public_url = drive_service.make_file_public(pdf_result['file_id'])

            # Save PDF info
            contract.gdrive_pdf_file_id = pdf_result['file_id']
            contract.gdrive_pdf_file_url = pdf_public_url
            contract.save()

            logger.info(f"PDF generated and made public: {pdf_public_url}")
        else:
            logger.info(f"Using existing PDF for contract {contract_id}")

        # Convert Google Drive URL to direct download format
        file_id = contract.gdrive_pdf_file_id
        direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        logger.info(f"Using direct download URL for Dropbox Sign: {direct_download_url}")

        # Create signature request via Dropbox Sign
        dropbox_service = DropboxSignService()
        signature_request = dropbox_service.create_signature_request(
            file_url=direct_download_url,
            signers=signers_data,
            title=contract.title,
            test_mode=test_mode
        )

        # Update contract
        contract.dropbox_sign_request_id = signature_request.signature_request_id
        contract.status = 'pending_signature'
        contract.error_message = ''
        contract.save()

        # Create signature records
        for signer_data in signers_data:
            ContractSignature.objects.create(
                contract=contract,
                signer_email=signer_data['email'],
                signer_name=signer_data['name'],
                signer_role=signer_data.get('role', ''),
                status='pending',
                sent_at=timezone.now()
            )

        logger.info(f"Successfully sent contract {contract_id} for signature")

        # Return minimal data - frontend fetches full contract from database
        return {
            'success': True,
            'contract_id': contract_id
        }

    except Contract.DoesNotExist:
        error_msg = f"Contract {contract_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

    except Exception as e:
        error_msg = f"Failed to send for signature: {str(e)}"
        logger.error(f"Error sending contract {contract_id} for signature: {error_msg}")

        # Update contract with error status
        try:
            contract = Contract.objects.get(id=contract_id)
            contract.status = 'failed'
            contract.error_message = error_msg
            contract.save()
        except Exception as save_error:
            logger.error(f"Failed to update contract status: {str(save_error)}")

        return {'success': False, 'error': error_msg}
