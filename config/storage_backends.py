"""
Custom storage backends for AWS S3.

This module defines custom storage classes for handling media files
using AWS S3 when USE_S3 is enabled in settings.
"""

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """
    Custom storage backend for media files (user uploads, profile photos, etc.).

    Uses a separate bucket location and sets public read permissions
    for media files.
    """
    location = settings.AWS_MEDIA_LOCATION
    default_acl = 'public-read'
    file_overwrite = False
    custom_domain = False  # Use bucket URL, not CloudFront


class PrivateMediaStorage(S3Boto3Storage):
    """
    Custom storage backend for private media files (contracts, sensitive documents).

    Files stored with this backend are NOT publicly accessible.
    """
    location = settings.AWS_PRIVATE_MEDIA_LOCATION
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
