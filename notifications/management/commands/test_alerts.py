"""
Management command to test notification alert system.

Usage:
    python manage.py test_alerts [--all] [--tomorrow] [--urgent] [--inactive] [--campaigns] [--overdue]
"""

from django.core.management.base import BaseCommand
from notifications.tasks import (
    check_tasks_due_tomorrow,
    check_tasks_due_soon,
    check_inactive_tasks,
    check_campaigns_ending_soon,
    check_overdue_tasks,
)


class Command(BaseCommand):
    help = 'Test notification alert tasks manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all alert checks',
        )
        parser.add_argument(
            '--tomorrow',
            action='store_true',
            help='Check tasks due tomorrow',
        )
        parser.add_argument(
            '--urgent',
            action='store_true',
            help='Check tasks due in next few hours',
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Check tasks without updates',
        )
        parser.add_argument(
            '--campaigns',
            action='store_true',
            help='Check campaigns ending soon',
        )
        parser.add_argument(
            '--overdue',
            action='store_true',
            help='Check overdue tasks',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=4,
            help='Hours threshold for urgent deadline check (default: 4)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Days threshold for inactivity check (default: 7)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('= Testing Notification Alert System'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        run_all = options['all']
        results = []

        # Check tasks due tomorrow
        if run_all or options['tomorrow']:
            self.stdout.write('ð Checking tasks due tomorrow...')
            result = check_tasks_due_tomorrow()
            self.stdout.write(self.style.SUCCESS(f'    {result}'))
            results.append(result)
            self.stdout.write('')

        # Check urgent deadlines
        if run_all or options['urgent']:
            hours = options['hours']
            self.stdout.write(f'=¨ Checking tasks due in next {hours} hours...')
            result = check_tasks_due_soon(hours=hours)
            self.stdout.write(self.style.SUCCESS(f'    {result}'))
            results.append(result)
            self.stdout.write('')

        # Check inactive tasks
        if run_all or options['inactive']:
            days = options['days']
            self.stdout.write(f'   Checking tasks inactive for {days}+ days...')
            result = check_inactive_tasks(days_threshold=days)
            self.stdout.write(self.style.SUCCESS(f'    {result}'))
            results.append(result)
            self.stdout.write('')

        # Check campaigns ending soon
        if run_all or options['campaigns']:
            self.stdout.write('=Å Checking campaigns ending soon...')
            result = check_campaigns_ending_soon()
            self.stdout.write(self.style.SUCCESS(f'    {result}'))
            results.append(result)
            self.stdout.write('')

        # Check overdue tasks
        if run_all or options['overdue']:
            self.stdout.write('=4 Checking overdue tasks...')
            result = check_overdue_tasks()
            self.stdout.write(self.style.SUCCESS(f'    {result}'))
            results.append(result)
            self.stdout.write('')

        if not results:
            self.stdout.write(self.style.WARNING('No checks selected. Use --all or specify individual checks.'))
            self.stdout.write(self.style.WARNING('Run with --help to see available options.'))
        else:
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('( Alert checks completed!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
