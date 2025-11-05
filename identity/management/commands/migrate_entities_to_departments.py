"""
Management command to migrate existing entities to department-scoped model.

This command adds all existing entities to the Digital department
(since Digital department was the only one adding entities to the database).

Entities with internal roles are NOT added to DepartmentEntity as they are
visible to all departments by default via the is_internal flag.

Usage:
    python manage.py migrate_entities_to_departments
    python manage.py migrate_entities_to_departments --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from identity.models import Entity, DepartmentEntity
from api.models import Department


class Command(BaseCommand):
    help = 'Migrate existing entities to Digital department'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        # Get Digital department
        try:
            digital_dept = Department.objects.get(code='digital')
        except Department.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                'Digital department not found! Please ensure department with code="digital" exists.'
            ))
            return

        self.stdout.write(f'Found department: {digital_dept.name} (code: {digital_dept.code})')

        # Get all entities
        all_entities = Entity.objects.all()
        total_entities = all_entities.count()

        self.stdout.write(f'\nFound {total_entities} total entities')

        # Separate internal vs external entities
        internal_entities = []
        external_entities = []

        for entity in all_entities:
            has_internal_role = entity.entity_roles.filter(is_internal=True).exists()
            if has_internal_role:
                internal_entities.append(entity)
            else:
                external_entities.append(entity)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ {len(internal_entities)} entities with internal roles (visible to all departments)'
        ))
        self.stdout.write(
            f'  {len(external_entities)} external entities to add to Digital department\n'
        )

        if not dry_run:
            with transaction.atomic():
                created_count = 0
                skipped_count = 0

                for entity in external_entities:
                    dept_entity, created = DepartmentEntity.objects.get_or_create(
                        entity=entity,
                        department=digital_dept,
                        defaults={
                            'added_by': None,  # System migration
                            'is_active': True
                        }
                    )

                    if created:
                        created_count += 1
                        if created_count <= 10:  # Show first 10
                            self.stdout.write(f'  → Added: {entity.display_name}')
                    else:
                        skipped_count += 1

                if created_count > 10:
                    self.stdout.write(f'  ... and {created_count - 10} more')

                if skipped_count > 0:
                    self.stdout.write(self.style.WARNING(
                        f'\n⚠ {skipped_count} entities already had DepartmentEntity records'
                    ))

                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Successfully added {created_count} entities to Digital department'
                ))

        else:
            # Dry run - show what would happen
            self.stdout.write(self.style.WARNING('\nEntities that would be added to Digital department:'))
            for i, entity in enumerate(external_entities[:20], 1):
                self.stdout.write(f'  {i}. {entity.display_name} ({entity.get_kind_display()})')

            if len(external_entities) > 20:
                self.stdout.write(f'  ... and {len(external_entities) - 20} more')

            self.stdout.write(self.style.WARNING(
                f'\n→ Would create {len(external_entities)} DepartmentEntity records'
            ))

        # Show internal entities summary
        if internal_entities:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ {len(internal_entities)} internal entities will remain visible to all departments:'
            ))
            for i, entity in enumerate(internal_entities[:10], 1):
                roles = ', '.join([r.get_role_display() for r in entity.entity_roles.filter(is_internal=True)])
                self.stdout.write(f'  {i}. {entity.display_name} ({roles})')

            if len(internal_entities) > 10:
                self.stdout.write(f'  ... and {len(internal_entities) - 10} more')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nRun without --dry-run to apply these changes'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Migration completed successfully!'))
