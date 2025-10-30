"""
Google Drive API integration for contract templates and storage.
Uses Service Account authentication.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from decouple import config
import io
import json
from pathlib import Path


class GoogleDriveService:
    """
    Service for interacting with Google Drive API.
    """

    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self):
        """
        Initialize Google Drive service with service account credentials.
        """
        # Load service account credentials from JSON file
        service_account_file = config('GOOGLE_SERVICE_ACCOUNT_FILE', default='service-account.json')

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=self.SCOPES
        )

        self.service = build('drive', 'v3', credentials=credentials)

    def get_file(self, file_id):
        """
        Get file metadata from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dict
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, webViewLink, createdTime, modifiedTime'
            ).execute()
            return file
        except HttpError as error:
            raise Exception(f'Error getting file: {error}')

    def download_file(self, file_id):
        """
        Download file content from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            return file_content.getvalue()
        except HttpError as error:
            raise Exception(f'Error downloading file: {error}')

    def upload_file(self, file_path, file_name, folder_id=None, mime_type=None):
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local path to the file
            file_name: Name for the file in Google Drive
            folder_id: Optional folder ID to upload to
            mime_type: Optional MIME type of the file

        Returns:
            File ID and web view link dict
        """
        try:
            file_metadata = {'name': file_name}

            if folder_id:
                file_metadata['parents'] = [folder_id]

            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()

            return {
                'file_id': file.get('id'),
                'web_view_link': file.get('webViewLink')
            }
        except HttpError as error:
            raise Exception(f'Error uploading file: {error}')

    def upload_file_content(self, content, file_name, folder_id=None, mime_type='application/pdf'):
        """
        Upload file content directly to Google Drive (from memory).

        Args:
            content: File content as bytes
            file_name: Name for the file in Google Drive
            folder_id: Optional folder ID to upload to
            mime_type: MIME type of the file

        Returns:
            File ID and web view link dict
        """
        try:
            file_metadata = {'name': file_name}

            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Create a BytesIO object from content
            media = MediaIoBaseUpload(
                io.BytesIO(content),
                mimetype=mime_type,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()

            return {
                'file_id': file.get('id'),
                'web_view_link': file.get('webViewLink')
            }
        except HttpError as error:
            raise Exception(f'Error uploading file content: {error}')

    def copy_file_old(self, file_id, new_name, folder_id=None):
        """
        Create a copy of a file in Google Drive using the copy API.
        (Old method - may fail with quota issues)

        Args:
            file_id: ID of the file to copy
            new_name: Name for the copied file
            folder_id: Optional folder ID to copy to

        Returns:
            New file ID and web view link dict
        """
        try:
            body = {'name': new_name}

            if folder_id:
                body['parents'] = [folder_id]

            file = self.service.files().copy(
                fileId=file_id,
                body=body,
                fields='id, webViewLink'
            ).execute()

            return {
                'file_id': file.get('id'),
                'web_view_link': file.get('webViewLink')
            }
        except HttpError as error:
            raise Exception(f'Error copying file: {error}')

    def copy_file(self, file_id, new_name, folder_id=None):
        """
        Create a copy of a file in Google Drive by downloading and re-uploading.
        This method avoids quota issues with the copy API.

        Args:
            file_id: ID of the file to copy
            new_name: Name for the copied file
            folder_id: Optional folder ID to copy to

        Returns:
            New file ID and web view link dict
        """
        try:
            # Get file metadata to determine type
            file_meta = self.service.files().get(
                fileId=file_id,
                fields='mimeType'
            ).execute()

            mime_type = file_meta.get('mimeType')

            # For Google Docs, export as .docx then import back as Google Doc
            if mime_type == 'application/vnd.google-apps.document':
                # Export as .docx
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )

                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)

                done = False
                while not done:
                    status, done = downloader.next_chunk()

                # Upload back as Google Doc
                file_metadata = {
                    'name': new_name,
                    'mimeType': 'application/vnd.google-apps.document'
                }

                if folder_id:
                    file_metadata['parents'] = [folder_id]

                media = MediaIoBaseUpload(
                    file_content,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    resumable=True
                )

                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()

                return {
                    'file_id': file.get('id'),
                    'web_view_link': file.get('webViewLink')
                }
            else:
                # For regular files, download and re-upload
                file_content = self.download_file(file_id)

                file_metadata = {'name': new_name}
                if folder_id:
                    file_metadata['parents'] = [folder_id]

                media = MediaIoBaseUpload(
                    io.BytesIO(file_content),
                    mimetype=mime_type,
                    resumable=True
                )

                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()

                return {
                    'file_id': file.get('id'),
                    'web_view_link': file.get('webViewLink')
                }

        except HttpError as error:
            raise Exception(f'Error copying file: {error}')

    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder
            parent_folder_id: Optional parent folder ID

        Returns:
            Folder ID
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]

            folder = self.service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()

            return folder.get('id')
        except HttpError as error:
            raise Exception(f'Error creating folder: {error}')

    def list_files_in_folder(self, folder_id):
        """
        List all files in a folder.

        Args:
            folder_id: Folder ID

        Returns:
            List of files
        """
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id, name, mimeType, webViewLink, createdTime, modifiedTime)'
            ).execute()

            return results.get('files', [])
        except HttpError as error:
            raise Exception(f'Error listing files: {error}')

    def make_file_public(self, file_id):
        """
        Make a file publicly accessible with a shareable link.

        Args:
            file_id: Google Drive file ID

        Returns:
            Public share URL
        """
        try:
            # Create public permission
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }

            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                supportsAllDrives=True
            ).execute()

            # Get the updated file with webViewLink
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink',
                supportsAllDrives=True
            ).execute()

            return file.get('webViewLink')
        except HttpError as error:
            raise Exception(f'Error making file public: {error}')

    def search_files(self, query=None, mime_type=None, limit=20):
        """
        Search for files in Google Drive.

        Args:
            query: Search query string
            mime_type: Filter by MIME type (e.g., 'application/vnd.google-apps.document')
            limit: Maximum number of results

        Returns:
            List of files matching search criteria
        """
        try:
            # Build query
            q_parts = ["trashed=false"]

            if query:
                # Escape single quotes and backslashes for Google Drive API query safety
                escaped_query = query.replace('\\', '\\\\').replace("'", "\\'")
                q_parts.append(f"name contains '{escaped_query}'")

            if mime_type:
                q_parts.append(f"mimeType='{mime_type}'")

            q_string = " and ".join(q_parts)

            results = self.service.files().list(
                q=q_string,
                pageSize=limit,
                fields='files(id, name, mimeType, webViewLink, iconLink, createdTime, modifiedTime, owners)',
                orderBy='modifiedTime desc'
            ).execute()

            return results.get('files', [])
        except HttpError as error:
            raise Exception(f'Error searching files: {error}')

    def search_folders(self, query=None, limit=20):
        """
        Search for folders in Google Drive.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of folders matching search criteria
        """
        return self.search_files(
            query=query,
            mime_type='application/vnd.google-apps.folder',
            limit=limit
        )

    def search_documents(self, query=None, limit=20):
        """
        Search for Google Docs documents.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of Google Docs matching search criteria
        """
        return self.search_files(
            query=query,
            mime_type='application/vnd.google-apps.document',
            limit=limit
        )
