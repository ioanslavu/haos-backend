"""
Management command to import digital clients from CSV file.

Imports companies/entities that work with the digital department.
Creates Entity, EntityRole, and ContactPerson records.

Usage:
    python manage.py import_digital_clients [--csv-path PATH] [--dry-run]
"""

import csv
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from identity.models import Entity, EntityRole, ContactPerson, ContactEmail, ContactPhone


class Command(BaseCommand):
    help = 'Import digital clients from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='digital-clients.csv',
            help='Path to CSV file (default: digital-clients.csv)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving to database',
        )

    def clean_phone(self, phone):
        """Extract only digits from phone number."""
        if not phone:
            return ''
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        return digits

    def clean_email(self, email):
        """Clean and validate email."""
        if not email:
            return ''
        # Remove extra characters like >
        email = email.strip().rstrip('>')
        return email

    def auto_fix_row(self, row, row_num):
        """Auto-fix known data issues in CSV."""
        # Row 6: Emails are swapped
        if row_num == 6:
            # Name column has email, email column has email
            name = row['cotnact partner name']
            email = row['contact partner mail']
            if '@' in name and '@' in email:
                # Both are emails, swap them
                self.stdout.write(
                    self.style.WARNING(
                        f'  Auto-fix row {row_num}: Swapping emails ({name} ↔ {email})'
                    )
                )
                row['cotnact partner name'] = 'HG Media Team'  # Placeholder
                row['contact partner mail'] = email  # Keep second one

        # Row 18: Name and phone swapped
        if row_num == 18:
            name = row['cotnact partner name']
            phone = row['contact partner phone number']
            if '@' in name and not '@' in phone:
                # Name has email, phone has name
                self.stdout.write(
                    self.style.WARNING(
                        f'  Auto-fix row {row_num}: Swapping name/phone'
                    )
                )
                row['cotnact partner name'], row['contact partner phone number'] = phone, name

        return row

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']

        # Find CSV file
        csv_file = Path(csv_path)
        if not csv_file.exists():
            # Try in project root
            csv_file = Path(__file__).resolve().parent.parent.parent.parent.parent / csv_path
            if not csv_file.exists():
                raise CommandError(f'CSV file not found: {csv_path}')

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('IMPORT DIGITAL CLIENTS FROM CSV'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be saved\n'))
        else:
            self.stdout.write(self.style.NOTICE('\n📥 IMPORT MODE - Data will be imported\n'))

        self.stdout.write(f'Reading CSV: {csv_file}\n')

        # Read CSV
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total = len(rows)
        self.stdout.write(f'Found {total} rows\n')

        created_entities = 0
        created_contacts = 0
        skipped_contacts = 0
        errors = 0

        for idx, row in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
            try:
                # Auto-fix known issues
                row = self.auto_fix_row(row, idx)

                # Extract data
                business_name = row['business name'].strip()
                alias = row['alias'].strip() if row['alias'] else ''
                entity_type = row['type'].strip() if row['type'] else ''
                contact_name = row['cotnact partner name'].strip() if row['cotnact partner name'] else ''
                contact_email = self.clean_email(row['contact partner mail']) if row['contact partner mail'] else ''
                contact_phone = self.clean_phone(row['contact partner phone number']) if row['contact partner phone number'] else ''

                if not business_name:
                    self.stdout.write(
                        self.style.WARNING(f'  ⏭️  Row {idx}: Skipping empty business name')
                    )
                    continue

                if dry_run:
                    # Preview
                    roles = ['digital']
                    if entity_type.lower() == 'artist':
                        roles.append('artist')
                    elif entity_type.lower() == 'label':
                        roles.append('label')

                    has_contact = bool(contact_name or contact_email)
                    contact_info = f', contact: {contact_name}' if has_contact else ', no contact'

                    self.stdout.write(
                        f'  📋 {business_name} (alias: {alias or "none"}, roles: {", ".join(roles)}{contact_info})'
                    )
                    created_entities += 1
                    if has_contact:
                        created_contacts += 1
                    else:
                        skipped_contacts += 1
                    continue

                # Create Entity
                with transaction.atomic():
                    # Check if entity exists
                    existing = Entity.objects.filter(display_name=business_name).first()

                    if existing:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⏭️  {business_name}: Already exists (skipping)'
                            )
                        )
                        continue

                    entity = Entity.objects.create(
                        kind='PJ',
                        display_name=business_name,
                        alias_name=alias if alias else '',
                    )

                    # Create EntityRoles
                    roles_created = []

                    # All get digital role (primary)
                    EntityRole.objects.create(
                        entity=entity,
                        role='digital',
                        primary_role=True,
                        is_internal=False,
                    )
                    roles_created.append('digital')

                    # Add artist or label role if specified
                    if entity_type.lower() == 'artist':
                        EntityRole.objects.create(
                            entity=entity,
                            role='artist',
                            primary_role=False,
                            is_internal=False,
                        )
                        roles_created.append('artist')
                    elif entity_type.lower() == 'label':
                        EntityRole.objects.create(
                            entity=entity,
                            role='label',
                            primary_role=False,
                            is_internal=False,
                        )
                        roles_created.append('label')

                    # Create ContactPerson if contact info exists
                    contact_created = False
                    if contact_name or contact_email:
                        contact_person = ContactPerson.objects.create(
                            entity=entity,
                            name=contact_name or 'Contact',
                            role='partner',
                        )

                        # Add email as separate ContactEmail object
                        if contact_email:
                            ContactEmail.objects.create(
                                contact_person=contact_person,
                                email=contact_email,
                                label='Work',
                                is_primary=True
                            )

                        # Add phone as separate ContactPhone object
                        if contact_phone:
                            ContactPhone.objects.create(
                                contact_person=contact_person,
                                phone=contact_phone,
                                label='Work',
                                is_primary=True
                            )

                        contact_created = True
                        created_contacts += 1
                    else:
                        skipped_contacts += 1

                    contact_status = '📞 with contact' if contact_created else '⏭️ no contact'

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ {business_name} (alias: {alias or "none"}, '
                            f'roles: {", ".join(roles_created)}, {contact_status})'
                        )
                    )
                    created_entities += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ Row {idx} ({row.get("business name", "unknown")}): {str(e)}'
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
            self.stdout.write(f'Would create: {created_contacts} contact persons')
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Created: {created_entities} entities'))
            self.stdout.write(self.style.SUCCESS(f'✅ Created: {created_contacts} contact persons'))

        if skipped_contacts > 0:
            self.stdout.write(self.style.WARNING(f'⏭️  Skipped contacts: {skipped_contacts} (no contact info)'))

        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {errors}'))

        if not dry_run and created_entities > 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
