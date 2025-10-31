"""
Management command to export artists to a JSON fixture file.

This creates a portable fixture that can be imported into any environment
(local, staging, production) with all artist data including:
- Entity details
- Entity roles
- Social media accounts
- Profile photo URLs (S3 or local)

Usage:
    python manage.py export_artists_fixture --output artists_fixture.json
"""

import json
from django.core.management.base import BaseCommand
from django.conf import settings
from identity.models import Entity, EntityRole, SocialMediaAccount


class Command(BaseCommand):
    help = 'Export internal artists to a JSON fixture file for deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='artists_fixture.json',
            help='Output JSON file path (default: artists_fixture.json)',
        )
        parser.add_argument(
            '--internal-only',
            action='store_true',
            help='Export only internal artists (is_internal=True)',
        )

    def handle(self, *args, **options):
        output_file = options['output']
        internal_only = options['internal_only']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('EXPORT ARTISTS TO JSON FIXTURE'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Get entities to export
        if internal_only:
            entities = Entity.objects.filter(
                entity_roles__is_internal=True
            ).distinct().order_by('display_name')
            self.stdout.write(f'Exporting internal artists only...')
        else:
            entities = Entity.objects.all().order_by('display_name')
            self.stdout.write(f'Exporting all entities...')

        total = entities.count()
        self.stdout.write(f'Found {total} entities to export\n')

        fixture_data = []

        for entity in entities:
            # Build entity data
            entity_data = {
                'kind': entity.kind,
                'display_name': entity.display_name,
                'first_name': entity.first_name,
                'last_name': entity.last_name,
                'stage_name': entity.stage_name or '',
                'nationality': entity.nationality or '',
                'gender': entity.gender,
                'email': entity.email or '',
                'phone': entity.phone or '',
                'address': entity.address or '',
                'city': entity.city or '',
                'state': entity.state or '',
                'zip_code': entity.zip_code or '',
                'country': entity.country or '',
                'notes': entity.notes or '',
            }

            # Add profile photo URL
            if entity.profile_photo:
                if settings.USE_S3:
                    # S3 URL - use the full URL
                    entity_data['profile_photo_url'] = entity.profile_photo.url
                else:
                    # Local URL - store relative path
                    entity_data['profile_photo_url'] = entity.profile_photo.url

            # Get entity roles
            entity_data['roles'] = []
            for role in entity.entity_roles.all():
                entity_data['roles'].append({
                    'role': role.role,
                    'primary_role': role.primary_role,
                    'is_internal': role.is_internal,
                })

            # Get social media accounts
            entity_data['social_media'] = []
            for account in entity.social_media_accounts.all():
                entity_data['social_media'].append({
                    'platform': account.platform,
                    'handle': account.handle or '',
                    'url': account.url,
                    'display_name': account.display_name or '',
                    'follower_count': account.follower_count,
                    'is_verified': account.is_verified,
                    'is_primary': account.is_primary,
                    'notes': account.notes or '',
                })

            fixture_data.append(entity_data)
            self.stdout.write(f'  ✅ {entity.display_name} ({len(entity_data["roles"])} roles, {len(entity_data["social_media"])} social accounts)')

        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(fixture_data, f, indent=2, ensure_ascii=False)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Exported {total} entities to {output_file}'))
        self.stdout.write('')
        self.stdout.write('Import on another server with:')
        self.stdout.write(self.style.NOTICE(f'  python manage.py import_entities_fixture {output_file}'))
