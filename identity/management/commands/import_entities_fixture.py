"""
Management command to import entities from a JSON fixture file.

This command can import entities with:
- Profile photos from S3 URLs (downloads and stores locally or re-uploads to S3)
- Profile photos from local files
- Profile photos from HTTP URLs (downloads them)
- Social media accounts
- Entity roles

Supports both fresh imports and updates to existing entities.

Usage:
    # Import from JSON file
    python manage.py import_entities_fixture artists_fixture.json

    # Dry run (preview what will be imported)
    python manage.py import_entities_fixture artists_fixture.json --dry-run

    # Skip downloading photos (useful if photos already uploaded separately)
    python manage.py import_entities_fixture artists_fixture.json --skip-photos

    # Update existing entities instead of skipping them
    python manage.py import_entities_fixture artists_fixture.json --update-existing
"""

import json
import requests
from io import BytesIO
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from identity.models import Entity, EntityRole, SocialMediaAccount


class Command(BaseCommand):
    help = 'Import entities from JSON fixture file'

    def add_arguments(self, parser):
        parser.add_argument(
            'fixture_file',
            type=str,
            help='Path to JSON fixture file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving to database',
        )
        parser.add_argument(
            '--skip-photos',
            action='store_true',
            help='Skip downloading/importing profile photos',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing entities instead of skipping them',
        )

    def handle(self, *args, **options):
        fixture_file = options['fixture_file']
        dry_run = options['dry_run']
        skip_photos = options['skip_photos']
        update_existing = options['update_existing']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('IMPORT ENTITIES FROM FIXTURE'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be saved\n'))
        else:
            self.stdout.write(self.style.NOTICE('\n📥 IMPORT MODE - Entities will be created/updated\n'))

        # Load JSON fixture
        try:
            with open(fixture_file, 'r', encoding='utf-8') as f:
                fixture_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Fixture file not found: {fixture_file}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in fixture file: {e}')

        total = len(fixture_data)
        self.stdout.write(f'Loaded {total} entities from {fixture_file}\n')

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for entity_data in fixture_data:
            try:
                with transaction.atomic():
                    # Check if entity exists
                    existing = Entity.objects.filter(
                        display_name=entity_data['display_name']
                    ).first()

                    if existing and not update_existing:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⏭️  {entity_data["display_name"]}: Already exists (skipping)'
                            )
                        )
                        skipped += 1
                        continue

                    if dry_run:
                        action = 'Would update' if existing else 'Would create'
                        self.stdout.write(
                            f'  📋 {entity_data["display_name"]}: {action} '
                            f'({len(entity_data.get("roles", []))} roles, '
                            f'{len(entity_data.get("social_media", []))} social accounts)'
                        )
                        created += 1
                        continue

                    # Create or update entity
                    if existing:
                        entity = existing
                        action = 'Updated'
                    else:
                        entity = Entity()
                        action = 'Created'

                    # Set basic fields
                    entity.kind = entity_data['kind']
                    entity.display_name = entity_data['display_name']
                    entity.first_name = entity_data.get('first_name', '')
                    entity.last_name = entity_data.get('last_name', '')
                    entity.stage_name = entity_data.get('stage_name', '')
                    entity.nationality = entity_data.get('nationality', '')
                    entity.gender = entity_data.get('gender')
                    entity.email = entity_data.get('email', '')
                    entity.phone = entity_data.get('phone', '')
                    entity.address = entity_data.get('address', '')
                    entity.city = entity_data.get('city', '')
                    entity.state = entity_data.get('state', '')
                    entity.zip_code = entity_data.get('zip_code', '')
                    entity.country = entity_data.get('country', '')
                    entity.notes = entity_data.get('notes', '')

                    # Save entity first to get ID
                    entity.save()

                    # Handle profile photo
                    if not skip_photos and entity_data.get('profile_photo_url'):
                        photo_url = entity_data['profile_photo_url']

                        try:
                            # Download photo from URL
                            response = requests.get(photo_url, timeout=30)
                            response.raise_for_status()

                            # Extract filename from URL
                            filename = photo_url.split('/')[-1].split('?')[0]  # Remove query params

                            # Save photo
                            entity.profile_photo.save(
                                filename,
                                ContentFile(response.content),
                                save=True
                            )
                            photo_status = '📷'
                        except Exception as e:
                            photo_status = f'⚠️ Photo error: {str(e)[:30]}'
                    else:
                        photo_status = '⏭️ Photo skipped' if skip_photos else ''

                    # Clear and recreate entity roles
                    if existing:
                        entity.entity_roles.all().delete()

                    for role_data in entity_data.get('roles', []):
                        EntityRole.objects.create(
                            entity=entity,
                            role=role_data['role'],
                            primary_role=role_data.get('primary_role', False),
                            is_internal=role_data.get('is_internal', False),
                        )

                    # Clear and recreate social media accounts
                    if existing:
                        entity.social_media_accounts.all().delete()

                    for social_data in entity_data.get('social_media', []):
                        SocialMediaAccount.objects.create(
                            entity=entity,
                            platform=social_data['platform'],
                            handle=social_data.get('handle', ''),
                            url=social_data['url'],
                            display_name=social_data.get('display_name', ''),
                            follower_count=social_data.get('follower_count'),
                            is_verified=social_data.get('is_verified', False),
                            is_primary=social_data.get('is_primary', False),
                            notes=social_data.get('notes', ''),
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ {entity.display_name}: {action} '
                            f'({len(entity_data.get("roles", []))} roles, '
                            f'{len(entity_data.get("social_media", []))} social) {photo_status}'
                        )
                    )

                    if existing:
                        updated += 1
                    else:
                        created += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {entity_data.get("display_name", "Unknown")}: Error - {str(e)}'
                    )
                )
                errors += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(f'Would create: {created} entities')
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Created: {created} entities'))
            if updated > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Updated: {updated} entities'))

        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'⏭️  Skipped: {skipped} entities (already exist)'))

        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors} entities'))

        if not dry_run and (created > 0 or updated > 0):
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
