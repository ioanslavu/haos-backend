"""
Management command to export digital clients to JSON fixture.

Exports all entities with 'digital' role for production deployment.
Includes Entity, EntityRole, ContactPerson, and contact details.

Usage:
    python manage.py export_digital_clients [--output PATH]
"""

import json
from pathlib import Path
from django.core.management.base import BaseCommand
from identity.models import Entity, EntityRole, ContactPerson


class Command(BaseCommand):
    help = 'Export digital clients to JSON fixture for production deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='digital_clients_fixture.json',
            help='Output file path (default: digital_clients_fixture.json)',
        )

    def handle(self, *args, **options):
        output_path = options['output']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('EXPORT DIGITAL CLIENTS TO FIXTURE'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Get all entities with digital role
        digital_role_ids = EntityRole.objects.filter(role='digital').values_list('entity_id', flat=True)
        entities = Entity.objects.filter(id__in=digital_role_ids).order_by('display_name')

        total = entities.count()
        self.stdout.write(f'Found {total} entities with digital role\n')

        fixture_data = []

        for entity in entities:
            self.stdout.write(f'  📋 {entity.display_name}')

            # Build entity data
            entity_data = {
                'kind': entity.kind,
                'display_name': entity.display_name,
                'alias_name': entity.alias_name or '',
                'email': entity.email or '',
                'phone': entity.phone or '',
                'address': entity.address or '',
                'city': entity.city or '',
                'state': entity.state or '',
                'zip_code': entity.zip_code or '',
                'country': entity.country or '',
                'company_registration_number': entity.company_registration_number or '',
                'vat_number': entity.vat_number or '',
                'iban': entity.iban or '',
                'bank_name': entity.bank_name or '',
                'bank_branch': entity.bank_branch or '',
                'notes': entity.notes or '',
            }

            # Get roles
            roles = []
            for role in entity.entity_roles.all():
                roles.append({
                    'role': role.role,
                    'primary_role': role.primary_role,
                    'is_internal': role.is_internal,
                })
            entity_data['roles'] = roles

            # Get contact persons
            contacts = []
            for contact in entity.contact_persons.all():
                contact_data = {
                    'name': contact.name,
                    'role': contact.role or '',
                    'engagement_stage': contact.engagement_stage or '',
                    'sentiment': contact.sentiment or '',
                    'notes': contact.notes or '',
                }

                # Get emails
                emails = []
                for email in contact.emails.all():
                    emails.append({
                        'email': email.email,
                        'label': email.label or '',
                        'is_primary': email.is_primary,
                    })
                contact_data['emails'] = emails

                # Get phones
                phones = []
                for phone in contact.phones.all():
                    phones.append({
                        'phone': phone.phone,
                        'label': phone.label or '',
                        'is_primary': phone.is_primary,
                    })
                contact_data['phones'] = phones

                contacts.append(contact_data)

            entity_data['contact_persons'] = contacts

            fixture_data.append(entity_data)

        # Write fixture to file
        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(fixture_data, f, indent=2, ensure_ascii=False)

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✅ Exported: {total} digital clients'))
        self.stdout.write(self.style.SUCCESS(f'✅ Output file: {output_file.absolute()}'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Export completed successfully!'))
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('To import on production server:'))
        self.stdout.write(f'  python manage.py import_digital_clients_fixture --fixture {output_path}')
