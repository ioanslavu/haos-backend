"""
Dropbox Sign API integration for contract signatures.
"""
from dropbox_sign import ApiClient, ApiException, Configuration, apis, models
from decouple import config


class DropboxSignService:
    """
    Service for interacting with Dropbox Sign API.
    """

    def __init__(self):
        """
        Initialize Dropbox Sign API client.
        """
        configuration = Configuration(
            username=config('DROPBOX_SIGN_API_KEY')
        )
        self.api_client = ApiClient(configuration)
        self.signature_request_api = apis.SignatureRequestApi(self.api_client)

    def create_signature_request(
        self,
        file_url,
        signers,
        title,
        subject=None,
        message=None,
        test_mode=True
    ):
        """
        Create a signature request.

        Args:
            file_url: URL to the file to be signed (can be a Google Drive file)
            signers: List of signer dicts with 'email' and 'name'
            title: Title of the signature request
            subject: Optional email subject
            message: Optional email message
            test_mode: Whether to use test mode (default True for development)

        Returns:
            Signature request object with request_id
        """
        try:
            # Build signers list
            signer_list = []
            for i, signer in enumerate(signers):
                signer_list.append(models.SubSignatureRequestSigner(
                    email_address=signer['email'],
                    name=signer['name'],
                    order=i
                ))

            # Create signature request
            data = models.SignatureRequestSendRequest(
                title=title,
                subject=subject or f"Please sign: {title}",
                message=message or "Please review and sign this document.",
                signers=signer_list,
                file_urls=[file_url],
                test_mode=test_mode
            )

            response = self.signature_request_api.signature_request_send(data)
            return response.signature_request

        except ApiException as e:
            raise Exception(f'Dropbox Sign API error: {e}')

    def get_signature_request(self, signature_request_id):
        """
        Get signature request details.

        Args:
            signature_request_id: ID of the signature request

        Returns:
            Signature request object
        """
        try:
            response = self.signature_request_api.signature_request_get(signature_request_id)
            return response.signature_request
        except ApiException as e:
            raise Exception(f'Dropbox Sign API error: {e}')

    def cancel_signature_request(self, signature_request_id):
        """
        Cancel a signature request.

        Args:
            signature_request_id: ID of the signature request to cancel

        Returns:
            None
        """
        try:
            self.signature_request_api.signature_request_cancel(signature_request_id)
        except ApiException as e:
            raise Exception(f'Dropbox Sign API error: {e}')

    def remind_signature_request(self, signature_request_id, email_address):
        """
        Send a reminder to a signer.

        Args:
            signature_request_id: ID of the signature request
            email_address: Email of the signer to remind

        Returns:
            Signature request object
        """
        try:
            data = models.SignatureRequestRemindRequest(email_address=email_address)
            response = self.signature_request_api.signature_request_remind(
                signature_request_id,
                data
            )
            return response.signature_request
        except ApiException as e:
            raise Exception(f'Dropbox Sign API error: {e}')

    def download_files(self, signature_request_id, file_type='pdf'):
        """
        Download signed files.

        Args:
            signature_request_id: ID of the signature request
            file_type: Type of file to download ('pdf' or 'zip')

        Returns:
            File content as bytes
        """
        try:
            response = self.signature_request_api.signature_request_files(
                signature_request_id,
                file_type=file_type
            )
            return response
        except ApiException as e:
            raise Exception(f'Dropbox Sign API error: {e}')

    def parse_webhook_event(self, event_data):
        """
        Parse Dropbox Sign webhook event.

        Args:
            event_data: Webhook event data dict

        Returns:
            Parsed event dict with event_type and relevant data
        """
        event = event_data.get('event', {})
        event_type = event.get('event_type')

        parsed = {
            'event_type': event_type,
            'signature_request_id': event.get('signature_request', {}).get('signature_request_id'),
            'timestamp': event.get('event_time'),
        }

        # Add signer-specific data for signature events
        if event_type in ['signature_request_signed', 'signature_request_declined', 'signature_request_viewed']:
            parsed['signer_email'] = event.get('signer_email_address')
            parsed['signature_id'] = event.get('signature_id')

        return parsed
