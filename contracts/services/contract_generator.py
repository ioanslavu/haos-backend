"""
Contract generation service.
Handles placeholder replacement and document generation from templates.
"""
from .google_drive import GoogleDriveService
from googleapiclient.discovery import build
from google.oauth2 import service_account
from decouple import config
import tempfile
import os


class ContractGeneratorService:
    """
    Service for generating contracts from templates with placeholder replacement.
    """

    def __init__(self):
        self.drive_service = GoogleDriveService()

        # Initialize Google Docs API for document manipulation
        service_account_file = config('GOOGLE_SERVICE_ACCOUNT_FILE', default='service-account.json')
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/documents'
            ]
        )
        self.docs_service = build('docs', 'v1', credentials=credentials)

    def generate_contract(
        self,
        template_file_id,
        output_folder_id,
        output_file_name,
        placeholder_values
    ):
        """
        Generate a contract from a template by replacing placeholders.

        Args:
            template_file_id: Google Drive file ID of the template
            output_folder_id: Google Drive folder ID where contract will be saved
            output_file_name: Name for the generated contract
            placeholder_values: Dict of placeholder key-value pairs

        Returns:
            Dict with file_id and web_view_link of the generated contract
        """
        # Step 1: Copy the template to create a new document
        copy_result = self.drive_service.copy_file(
            file_id=template_file_id,
            new_name=output_file_name,
            folder_id=output_folder_id
        )

        new_file_id = copy_result['file_id']

        # Step 2: Read document content for debugging (before replacement)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Reading document content before placeholder replacement...")
        doc_text = self.get_document_text(new_file_id)

        # Step 3: Replace placeholders in the copied document
        self._replace_placeholders(new_file_id, placeholder_values)

        # Step 4: Return the new document details
        return copy_result

    def _replace_placeholders(self, document_id, placeholder_values):
        """
        Replace placeholders in a Google Docs document.

        Args:
            document_id: Google Docs document ID
            placeholder_values: Dict of placeholder key-value pairs
        """
        import logging
        logger = logging.getLogger(__name__)

        requests = []

        # Build replacement requests for each placeholder
        for key, value in placeholder_values.items():
            replacement_value = str(value) if value is not None else ''

            # Strip braces from key if they were included (handle incorrect template definitions)
            clean_key = key.strip('{}').strip()

            # Try multiple placeholder formats to handle different spacing
            # Format 1: {{key}} (no spaces)
            placeholder_no_space = f"{{{{{clean_key}}}}}"

            # Format 2: {{ key }} (with spaces)
            placeholder_with_space = f"{{{{ {clean_key} }}}}"

            logger.info(f"Replacing placeholder '{placeholder_no_space}' (and variants) with value '{replacement_value}'")

            # Add replacement for both formats
            for placeholder_format in [placeholder_no_space, placeholder_with_space]:
                requests.append({
                    'replaceAllText': {
                        'containsText': {
                            'text': placeholder_format,
                            'matchCase': False
                        },
                        'replaceText': replacement_value
                    }
                })

        # Log the requests being sent
        logger.info(f"Sending {len(requests)} replacement requests to Google Docs API")
        logger.debug(f"Replacement requests: {requests}")

        # Execute all replacements in a single batch
        if requests:
            try:
                result = self.docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                logger.info(f"Successfully replaced placeholders. Result: {result}")
                logger.info(f"Replies from API: {result.get('replies', [])}")
            except Exception as e:
                logger.error(f"Error replacing placeholders: {str(e)}")
                raise

    def get_document_text(self, document_id):
        """
        Retrieve all text content from a Google Docs document.
        Useful for debugging placeholder issues.

        Args:
            document_id: Google Docs document ID

        Returns:
            String containing all document text
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            document = self.docs_service.documents().get(documentId=document_id).execute()
            doc_content = document.get('body', {}).get('content', [])

            text_parts = []
            for element in doc_content:
                if 'paragraph' in element:
                    for text_run in element['paragraph'].get('elements', []):
                        if 'textRun' in text_run:
                            text_parts.append(text_run['textRun'].get('content', ''))

            full_text = ''.join(text_parts)
            logger.info(f"Document text preview (first 500 chars): {full_text[:500]}")
            return full_text
        except Exception as e:
            logger.error(f"Error reading document text: {str(e)}")
            return ""

    def export_as_pdf(self, document_id, output_path=None):
        """
        Export a Google Docs document as PDF.

        Args:
            document_id: Google Docs document ID
            output_path: Optional local path to save PDF

        Returns:
            PDF content as bytes
        """
        # Export document as PDF
        pdf_content = self.drive_service.service.files().export(
            fileId=document_id,
            mimeType='application/pdf'
        ).execute()

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_content)

        return pdf_content

    def generate_contract_with_pdf(
        self,
        template_file_id,
        output_folder_id,
        output_file_name,
        placeholder_values
    ):
        """
        Generate a contract and also create a PDF version.

        Args:
            template_file_id: Google Drive file ID of the template
            output_folder_id: Google Drive folder ID where contract will be saved
            output_file_name: Name for the generated contract
            placeholder_values: Dict of placeholder key-value pairs

        Returns:
            Dict with docs_file_id, docs_web_link, pdf_file_id, pdf_web_link
        """
        # Generate the contract (Google Docs)
        docs_result = self.generate_contract(
            template_file_id=template_file_id,
            output_folder_id=output_folder_id,
            output_file_name=output_file_name,
            placeholder_values=placeholder_values
        )

        # Export as PDF
        pdf_content = self.export_as_pdf(docs_result['file_id'])

        # Upload PDF to Google Drive
        pdf_result = self.drive_service.upload_file_content(
            content=pdf_content,
            file_name=f"{output_file_name}.pdf",
            folder_id=output_folder_id,
            mime_type='application/pdf'
        )

        return {
            'docs_file_id': docs_result['file_id'],
            'docs_web_link': docs_result['web_view_link'],
            'pdf_file_id': pdf_result['file_id'],
            'pdf_web_link': pdf_result['web_view_link']
        }
