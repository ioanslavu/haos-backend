"""
Management command to import digital clients from JSON fixture.

Imports entities with digital role from fixture file.
Creates Entity, EntityRole, ContactPerson, and contact details.

Usage:
    python manage.py import_digital_clients_fixture --fixture FILE [--dry-run] [--update-existing]
"""

import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from identity.models import Entity, EntityRole, ContactPerson, ContactEmail, ContactPhone


class Command(BaseCommand):
    help = 'Import digital clients from JSON fixture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture',
            type=str,
            required=True,
            help='Path to JSON fixture file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving to database',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing entities instead of skipping them',
        )

    def handle(self, *args, **options):
        fixture_path = options['fixture']
        dry_run = options['dry_run']
        update_existing = options['update_existing']

        # Find fixture file
        fixture_file = Path(fixture_path)
        if not fixture_file.exists():
            # Try in project root
            fixture_file = Path(__file__).resolve().parent.parent.parent.parent.parent / fixture_path
            if not fixture_file.exists():
                raise CommandError(f'Fixture file not found: {fixture_path}')

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('IMPORT DIGITAL CLIENTS FROM FIXTURE'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be saved\n'))
        else:
            self.stdout.write(self.style.NOTICE('\n📥 IMPORT MODE - Data will be imported\n'))

        self.stdout.write(f'Reading fixture: {fixture_file}\n')

        # Load fixture
        with open(fixture_file, 'r', encoding='utf-8') as f:
            fixture_data = json.load(f)

        total = len(fixture_data)
        self.stdout.write(f'Found {total} entities\n')

        created_entities = 0
        updated_entities = 0
        skipped_entities = 0
        created_contacts = 0
        errors = 0

        for idx, entity_data in enumerate(fixture_data, start=1):
            try:
                business_name = entity_data['display_name']

                if dry_run:
                    # Preview
                    roles = [r['role'] for r in entity_data.get('roles', [])]
                    contacts_count = len(entity_data.get('contact_persons', []))

                    self.stdout.write(
                        f'  📋 {business_name} (roles: {", ".join(roles)}, contacts: {contacts_count})'
                    )
                    created_entities += 1
                    continue

                # Check if entity exists
                with transaction.atomic():
                    existing = Entity.objects.filter(display_name=business_name).first()

                    if existing and not update_existing:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⏭️  {business_name}: Already exists (skipping)'
                            )
                        )
                        skipped_entities += 1
                        continue

                    if existing and update_existing:
                        # Update existing entity
                        entity = existing
                        for key, value in entity_data.items():
                            if key not in ['roles', 'contact_persons'] and hasattr(entity, key):
                                setattr(entity, key, value)
                        entity.save()
                        action = 'Updated'
                        updated_entities += 1
                    else:
                        # Create new entity
                        entity_fields = {k: v for k, v in entity_data.items()
                                       if k not in ['roles', 'contact_persons']}
                        entity = Entity.objects.create(**entity_fields)
                        action = 'Created'
                        created_entities += 1

                    # Create roles (clear existing if updating)
                    if update_existing and existing:
                        entity.entity_roles.all().delete()

                    roles_created = []
                    for role_data in entity_data.get('roles', []):
                        EntityRole.objects.create(
                            entity=entity,
                            role=role_data['role'],
                            primary_role=role_data.get('primary_role', False),
                            is_internal=role_data.get('is_internal', False),
                        )
                        roles_created.append(role_data['role'])

                    # Create contact persons (clear existing if updating)
                    if update_existing and existing:
                        entity.contact_persons.all().delete()

                    for contact_data in entity_data.get('contact_persons', []):
                        contact = ContactPerson.objects.create(
                            entity=entity,
                            name=contact_data['name'],
                            role=contact_data.get('role', ''),
                            engagement_stage=contact_data.get('engagement_stage', ''),
                            sentiment=contact_data.get('sentiment', ''),
                            notes=contact_data.get('notes', ''),
                        )

                        # Create emails
                        for email_data in contact_data.get('emails', []):
                            ContactEmail.objects.create(
                                contact_person=contact,
                                email=email_data['email'],
                                label=email_data.get('label', ''),
                                is_primary=email_data.get('is_primary', False),
                            )

                        # Create phones
                        for phone_data in contact_data.get('phones', []):
                            ContactPhone.objects.create(
                                contact_person=contact,
                                phone=phone_data['phone'],
                                label=phone_data.get('label', ''),
                                is_primary=phone_data.get('is_primary', False),
                            )

                        created_contacts += 1

                    contacts_count = len(entity_data.get('contact_persons', []))
                    contact_status = f'📞 {contacts_count} contacts' if contacts_count > 0 else '⏭️ no contacts'

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ {action}: {business_name} '
                            f'(roles: {", ".join(roles_created)}, {contact_status})'
                        )
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {entity_data.get("display_name", "unknown")}: {str(e)}'
                    )
                )
                errors += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(f'Would create: {created_entities} entities')
        else:
            if created_entities > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Created: {created_entities} entities'))
            if updated_entities > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Updated: {updated_entities} entities'))
            if created_contacts > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Created: {created_contacts} contact persons'))

        if skipped_entities > 0:
            self.stdout.write(self.style.WARNING(f'⏭️  Skipped: {skipped_entities} (already exist)'))

        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors}'))

        if not dry_run and (created_entities > 0 or updated_entities > 0):
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
