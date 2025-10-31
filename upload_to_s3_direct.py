#!/usr/bin/env python
"""
Direct S3 upload script that bypasses Django's storage backend.
Use this when Django server is running with old cached settings.
"""

import os
import sys
import boto3
from pathlib import Path
from decouple import config

# AWS Configuration from .env
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')

# Create S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_S3_REGION_NAME
)

# Local media directory
BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT = BASE_DIR / 'media' / 'entity_photos'

print("=" * 70)
print("DIRECT S3 UPLOAD (bypasses Django)")
print("=" * 70)
print(f"\nLocal directory: {MEDIA_ROOT}")
print(f"S3 Bucket: {AWS_STORAGE_BUCKET_NAME}")
print(f"S3 Region: {AWS_S3_REGION_NAME}\n")

if not MEDIA_ROOT.exists():
    print(f"❌ Media directory not found: {MEDIA_ROOT}")
    sys.exit(1)

# Get all image files
image_files = list(MEDIA_ROOT.glob('*.[jJ][pP][gG]')) + \
              list(MEDIA_ROOT.glob('*.[jJ][pP][eE][gG]')) + \
              list(MEDIA_ROOT.glob('*.[pP][nN][gG]'))

print(f"Found {len(image_files)} image files\n")

uploaded = 0
errors = 0

for image_file in image_files:
    try:
        # S3 key (path in bucket)
        s3_key = f"media/entity_photos/{image_file.name}"

        # Upload file
        with open(image_file, 'rb') as f:
            s3_client.put_object(
                Bucket=AWS_STORAGE_BUCKET_NAME,
                Key=s3_key,
                Body=f,
                ContentType='image/jpeg'
                # No ACL - bucket policy handles public access
            )

        file_size_kb = image_file.stat().st_size / 1024
        print(f"  ✅ {image_file.name} ({file_size_kb:.1f} KB)")
        uploaded += 1

    except Exception as e:
        print(f"  ❌ {image_file.name}: {str(e)}")
        errors += 1

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"✅ Uploaded: {uploaded} files")
if errors > 0:
    print(f"❌ Errors: {errors} files")

# Show S3 URLs
print("\nSample S3 URLs:")
for i, image_file in enumerate(image_files[:3]):
    url = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/entity_photos/{image_file.name}"
    print(f"  {url}")
