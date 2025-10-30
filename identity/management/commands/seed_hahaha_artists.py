"""
Django management command to seed HaHaHa Production artists into the database.
Usage: python manage.py seed_hahaha_artists
"""

import json
import os
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from identity.models import Entity, EntityRole, SocialMediaAccount


class Command(BaseCommand):
    help = 'Seed HaHaHa Production artists from scraped JSON data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-file',
            type=str,
            default='utils/scrapers/artists_complete_data.json',
            help='Path to the JSON file with artist data'
        )
        parser.add_argument(
            '--photos-dir',
            type=str,
            default='utils/scrapers/artist_photos',
            help='Path to the directory with artist photos'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any database changes'
        )
        parser.add_argument(
            '--skip-photos',
            action='store_true',
            help='Skip downloading/attaching profile photos'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        photos_dir = options['photos_dir']
        dry_run = options['dry_run']
        skip_photos = options['skip_photos']

        # Resolve paths relative to project root
        from django.conf import settings
        base_dir = settings.BASE_DIR.parent  # Go up from backend/ to project root
        json_path = base_dir / json_file
        photos_path = base_dir / photos_dir

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))

        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f'❌ JSON file not found: {json_path}'))
            return

        if not skip_photos and not photos_path.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Photos directory not found: {photos_path}'))
            skip_photos = True

        # Load artist data
        with open(json_path, 'r', encoding='utf-8') as f:
            artists_data = json.load(f)

        self.stdout.write(self.style.SUCCESS(f'📁 Loaded {len(artists_data)} artists from {json_path}'))

        # Statistics
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'social_media_added': 0,
            'photos_attached': 0,
        }

        # Process each artist
        for artist_data in artists_data:
            try:
                if dry_run:
                    self.stdout.write(f"\n📋 Would process: {artist_data['stage_name']} ({artist_data['role']})")
                    continue

                with transaction.atomic():
                    result = self._process_artist(artist_data, photos_path, skip_photos)
                    stats[result] += 1

            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"❌ Error processing {artist_data.get('stage_name', 'unknown')}: {e}"))

        # Print summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write('=' * 70)
        self.stdout.write(f"✅ Created: {stats['created']}")
        self.stdout.write(f"🔄 Updated: {stats['updated']}")
        self.stdout.write(f"⏭️  Skipped: {stats['skipped']}")
        self.stdout.write(f"❌ Errors: {stats['errors']}")

    def _process_artist(self, artist_data, photos_path, skip_photos):
        """Process a single artist and return the result status."""
        stage_name = artist_data['stage_name']
        full_name = artist_data['full_name']
        role = artist_data['role']

        self.stdout.write(f"\n📸 Processing: {stage_name} ({role})")

        # Check if entity already exists by stage name or display name
        entity = Entity.objects.filter(stage_name=stage_name).first()
        if not entity:
            entity = Entity.objects.filter(display_name=stage_name).first()

        is_new = entity is None

        if entity:
            self.stdout.write(f"   🔄 Updating existing entity: {entity.id}")
        else:
            self.stdout.write(f"   ✨ Creating new entity")

        # Parse full name into first and last name
        name_parts = full_name.split()
        first_name = name_parts[0] if len(name_parts) > 0 else full_name
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        # Create or update entity
        if not entity:
            entity = Entity.objects.create(
                kind='PF',  # Physical Person
                display_name=stage_name,
                first_name=first_name if first_name != stage_name else '',
                last_name=last_name,
                stage_name=stage_name if stage_name != full_name else '',
                country='Romania',
                nationality='Romanian',
            )
            self.stdout.write(self.style.SUCCESS(f"   ✅ Created entity: {entity.id}"))
        else:
            # Update existing entity
            entity.stage_name = stage_name if stage_name != full_name else entity.stage_name
            entity.first_name = first_name if first_name != stage_name else entity.first_name
            entity.last_name = last_name or entity.last_name
            entity.save()
            self.stdout.write(self.style.SUCCESS(f"   ✅ Updated entity: {entity.id}"))

        # Add/update EntityRole
        role_mapping = {
            'artist': 'artist',
            'producer': 'producer',
            'songwriter': 'lyricist',  # Map songwriter to lyricist
        }

        role_value = role_mapping.get(role, role)
        entity_role, created = EntityRole.objects.get_or_create(
            entity=entity,
            role=role_value,
            defaults={
                'primary_role': True,
                'is_internal': True,  # All HaHaHa Production artists are internal
            }
        )

        if not created:
            # Update is_internal if it was previously False
            if not entity_role.is_internal:
                entity_role.is_internal = True
                entity_role.save()
                self.stdout.write(f"   🔄 Updated role to is_internal=True")
        else:
            self.stdout.write(f"   ✅ Added role: {role_value} (internal)")

        # Process social media accounts
        social_media_added = 0
        for social in artist_data.get('social_media', []):
            platform = social['platform']
            url = social['url'].strip()

            # Skip if already exists
            if SocialMediaAccount.objects.filter(entity=entity, url=url).exists():
                continue

            # Extract handle from URL if possible
            handle = self._extract_handle(platform, url)

            SocialMediaAccount.objects.create(
                entity=entity,
                platform=platform,
                url=url,
                handle=handle,
                is_primary=social_media_added == 0,  # First one is primary
            )
            social_media_added += 1
            self.stdout.write(f"   📱 Added {platform}: {url}")

        if social_media_added > 0:
            self.stdout.write(self.style.SUCCESS(f"   ✅ Added {social_media_added} social media accounts"))

        # Attach profile photo (if available and not skipping)
        if not skip_photos and artist_data.get('photo_filename'):
            photo_filename = artist_data['photo_filename']
            photo_path = photos_path / photo_filename

            if photo_path.exists():
                # Upload photo to Entity
                try:
                    from django.core.files import File
                    with open(photo_path, 'rb') as f:
                        entity.profile_photo.save(photo_filename, File(f), save=True)
                    self.stdout.write(self.style.SUCCESS(f"   📷 Photo uploaded: {photo_filename}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Photo upload failed: {e}"))
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Photo file not found: {photo_path}"))

        return 'created' if is_new else 'updated'

    def _extract_handle(self, platform, url):
        """Extract username/handle from social media URL."""
        import re

        if platform == 'instagram':
            match = re.search(r'instagram\.com/([^/?]+)', url)
            return match.group(1) if match else ''

        elif platform == 'twitter':
            match = re.search(r'(?:twitter|x)\.com/([^/?]+)', url)
            return match.group(1) if match else ''

        elif platform == 'facebook':
            match = re.search(r'facebook\.com/([^/?]+)', url)
            return match.group(1) if match else ''

        elif platform == 'youtube':
            match = re.search(r'youtube\.com/(?:user/|channel/|c/|@)?([^/?]+)', url)
            return match.group(1) if match else ''

        elif platform == 'spotify':
            # Spotify uses artist IDs, not handles
            match = re.search(r'artist/([^/?]+)', url)
            return match.group(1) if match else ''

        elif platform == 'tiktok':
            match = re.search(r'tiktok\.com/@([^/?]+)', url)
            return match.group(1) if match else ''

        elif platform == 'soundcloud':
            match = re.search(r'soundcloud\.com/([^/?]+)', url)
            return match.group(1) if match else ''

        return ''
