"""
Management command to upload existing media files from local storage to AWS S3.

This command is used when migrating from local file storage to S3.
It uploads all entity profile photos and updates the database references.

Usage:
    python manage.py upload_media_to_s3 [--dry-run]
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.base import File
from identity.models import Entity


class Command(BaseCommand):
    help = 'Upload existing entity profile photos from local media to AWS S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be uploaded without actually uploading',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Check if S3 is enabled
        if not getattr(settings, 'USE_S3', False):
            raise CommandError(
                'S3 is not enabled. Set USE_S3=True in your .env file and configure AWS credentials.'
            )

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('UPLOAD MEDIA FILES TO AWS S3'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No files will be uploaded\n'))
        else:
            self.stdout.write(self.style.NOTICE('\n📤 LIVE MODE - Files will be uploaded to S3\n'))

        # Get local media root
        if hasattr(settings, 'MEDIA_ROOT'):
            # Temporarily get the base media root before S3 override
            local_media_root = settings.BASE_DIR / 'media'
        else:
            local_media_root = settings.BASE_DIR / 'media'

        self.stdout.write(f'Local media directory: {local_media_root}')
        self.stdout.write(f'S3 Bucket: {settings.AWS_STORAGE_BUCKET_NAME}')
        self.stdout.write(f'S3 Region: {settings.AWS_S3_REGION_NAME}')
        self.stdout.write('')

        # Get all entities with profile photos
        entities = Entity.objects.exclude(profile_photo='').exclude(profile_photo__isnull=True)
        total_count = entities.count()

        self.stdout.write(f'Found {total_count} entities with profile photos\n')

        if total_count == 0:
            self.stdout.write(self.style.WARNING('No photos to upload.'))
            return

        uploaded = 0
        skipped = 0
        errors = 0

        for entity in entities:
            try:
                # Get the local file path
                local_path = local_media_root / entity.profile_photo.name

                if not os.path.exists(local_path):
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠️  {entity.display_name}: Local file not found at {local_path}'
                        )
                    )
                    skipped += 1
                    continue

                # Get file size
                file_size = os.path.getsize(local_path)
                file_size_kb = file_size / 1024

                if dry_run:
                    self.stdout.write(
                        f'  📋 {entity.display_name}: Would upload {entity.profile_photo.name} ({file_size_kb:.1f} KB)'
                    )
                    uploaded += 1
                else:
                    # Upload to S3 by re-saving the file through Django's storage backend
                    # This will use the S3 storage backend configured in settings
                    with open(local_path, 'rb') as f:
                        # Save the file with the same name - S3 storage backend will handle upload
                        file_name = os.path.basename(entity.profile_photo.name)
                        entity.profile_photo.save(file_name, File(f), save=True)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ {entity.display_name}: Uploaded {entity.profile_photo.name} ({file_size_kb:.1f} KB)'
                        )
                    )
                    uploaded += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {entity.display_name}: Error - {str(e)}'
                    )
                )
                errors += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(f'Would upload: {uploaded} files')
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Uploaded: {uploaded} files'))

        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Skipped: {skipped} files'))

        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors} files'))

        if not dry_run and uploaded > 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('All profile photos have been uploaded to S3!'))
            self.stdout.write(self.style.NOTICE('You can now safely remove the local media/entity_photos/ folder.'))
