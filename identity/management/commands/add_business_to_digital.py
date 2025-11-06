"""
Management command to add all business entities to the digital department.

This creates DepartmentEntity records linking business entities to the digital department,
making them visible to digital department users.

Business roles include: client, brand, label, booking, endorsements,
publishing, productie, new_business, digital.

Usage:
    python manage.py add_business_to_digital [--dry-run]

Examples:
    # Preview what would be added (safe, no changes)
    python manage.py add_business_to_digital --dry-run

    # Actually add entities to digital department
    python manage.py add_business_to_digital
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.models import Department
from identity.models import Entity, EntityRole, DepartmentEntity


class Command(BaseCommand):
    help = 'Add all business entities to the digital department'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('ADD BUSINESS ENTITIES TO DIGITAL DEPARTMENT'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be saved\n'))
        else:
            self.stdout.write(self.style.NOTICE('\n📥 IMPORT MODE - Data will be added to database\n'))

        # Get digital department
        try:
            digital_dept = Department.objects.get(code='digital')
            self.stdout.write(f'✓ Found digital department: {digital_dept.name} (ID: {digital_dept.id})\n')
        except Department.DoesNotExist:
            raise CommandError('Digital department not found! Please create it first.')

        # Business roles
        business_roles = [
            'client', 'brand', 'label', 'booking', 'endorsements',
            'publishing', 'productie', 'new_business', 'digital'
        ]

        self.stdout.write(f'Looking for entities with business roles: {", ".join(business_roles)}\n')

        # Find all entities with business roles
        business_entities = Entity.objects.filter(
            entity_roles__role__in=business_roles
        ).distinct().order_by('display_name')

        total_entities = business_entities.count()
        self.stdout.write(f'Found {total_entities} business entities\n')

        if total_entities == 0:
            self.stdout.write(self.style.WARNING('No business entities found. Nothing to do.'))
            return

        # Check which ones are already linked
        existing_links = DepartmentEntity.objects.filter(
            department=digital_dept,
            entity__in=business_entities
        ).values_list('entity_id', flat=True)

        existing_count = len(existing_links)
        new_count = total_entities - existing_count

        self.stdout.write(f'  - Already linked to digital: {existing_count}')
        self.stdout.write(f'  - Need to be added: {new_count}\n')

        if new_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ All business entities are already linked to digital department!'))
            return

        # Preview or add entities
        added = 0
        skipped = 0

        self.stdout.write('Processing entities:\n')

        for entity in business_entities:
            # Check if already linked
            if entity.id in existing_links:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'  ⏭️  {entity.display_name} (ID: {entity.id}) - Already linked')
                    )
                skipped += 1
                continue

            # Get entity roles for display
            roles = entity.entity_roles.values_list('role', flat=True)
            roles_display = ', '.join(roles)

            if dry_run:
                self.stdout.write(
                    f'  ➕ Would add: {entity.display_name} (ID: {entity.id}, roles: {roles_display})'
                )
                added += 1
            else:
                try:
                    with transaction.atomic():
                        DepartmentEntity.objects.create(
                            entity=entity,
                            department=digital_dept,
                            added_by=None,  # System operation, no specific user
                            is_active=True
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ Added: {entity.display_name} (ID: {entity.id}, roles: {roles_display})'
                            )
                        )
                        added += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ❌ Error adding {entity.display_name} (ID: {entity.id}): {str(e)}'
                        )
                    )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(f'Would add: {added} entities')
            self.stdout.write(f'Already linked: {skipped} entities')
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE('Run without --dry-run to actually add entities'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Added: {added} entities'))
            self.stdout.write(self.style.WARNING(f'⏭️  Skipped: {skipped} entities (already linked)'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Operation completed successfully!'))
