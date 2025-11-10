"""
Management command to seed default alert configurations.

Run this after migrating the AlertConfiguration model:
    python manage.py seed_alert_configurations
"""

from django.core.management.base import BaseCommand
from catalog.models import AlertConfiguration


class Command(BaseCommand):
    help = 'Seeds default alert configurations for Song Workflow'

    def handle(self, *args, **options):
        """Create default alert configurations."""

        configurations = [
            {
                'alert_type': 'overdue',
                'enabled': True,
                'days_threshold': None,  # Immediate check
                'schedule_description': 'Daily at midnight',
                'notify_assigned_user': True,
                'notify_department_managers': True,
                'notify_song_creator': False,
                'priority': 'urgent',
                'title_template': 'OVERDUE: {song_title}',
                'message_template': '"{song_title}" is overdue in {stage} stage. Deadline was {deadline}.',
            },
            {
                'alert_type': 'deadline_approaching',
                'enabled': True,
                'days_threshold': 2,  # 2 days before deadline
                'schedule_description': 'Daily at midnight',
                'notify_assigned_user': True,
                'notify_department_managers': True,
                'notify_song_creator': False,
                'priority': 'important',
                'title_template': 'Deadline Approaching: {song_title}',
                'message_template': '"{song_title}" is due in 2 days ({deadline}). Please complete checklist items.',
            },
            {
                'alert_type': 'release_approaching',
                'enabled': True,
                'days_threshold': 7,  # 7 days before release
                'schedule_description': 'Daily at midnight',
                'notify_assigned_user': False,
                'notify_department_managers': False,  # Sent to specific departments instead
                'notify_song_creator': False,
                'priority': 'important',
                'title_template': 'Release in 7 Days: {song_title}',
                'message_template': '"{song_title}" is scheduled for release in 7 days ({release_date}). Ensure all distribution is complete.',
            },
            {
                'alert_type': 'checklist_incomplete',
                'enabled': False,  # Disabled by default (optional feature)
                'days_threshold': 3,  # After 3 days of being incomplete
                'schedule_description': 'Daily at midnight',
                'notify_assigned_user': True,
                'notify_department_managers': False,
                'notify_song_creator': False,
                'priority': 'important',
                'title_template': 'Incomplete Checklist Item: {song_title}',
                'message_template': 'The checklist item "{item_name}" for "{song_title}" has been incomplete for 3+ days. Please complete it.',
            },
        ]

        created_count = 0
        updated_count = 0

        for config_data in configurations:
            alert_type = config_data['alert_type']

            # Check if configuration already exists
            config, created = AlertConfiguration.objects.get_or_create(
                alert_type=alert_type,
                defaults=config_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created configuration for: {alert_type}')
                )
            else:
                # Update existing configuration with new defaults (preserving user changes if they modified it)
                # Only update if never modified by a user
                if not config.updated_by:
                    for key, value in config_data.items():
                        if key != 'alert_type':  # Don't update the primary key
                            setattr(config, key, value)
                    config.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated configuration for: {alert_type}')
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(f'⊘ Skipped (user-modified): {alert_type}')
                    )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'✓ Seeding complete: {created_count} created, {updated_count} updated')
        )
        self.stdout.write('')
        self.stdout.write(
            'You can now configure alerts from the frontend at: /settings/alerts'
        )
