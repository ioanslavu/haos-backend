"""
Django management command to create test users for role impersonation testing.

Usage:
    python manage.py create_test_users

This will create 5 test users with different roles:
- Guest
- Digital Manager
- Digital Employee
- Sales Manager
- Sales Employee
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test users for role impersonation testing'

    def handle(self, *args, **options):
        test_users = [
            {
                'email': 'test-guest@hahahaproduction.com',
                'first_name': 'Test',
                'last_name': 'Guest',
                'role': 'guest',
                'department': None,
            },
            {
                'email': 'test-digital-manager@hahahaproduction.com',
                'first_name': 'Test Digital',
                'last_name': 'Manager',
                'role': 'digital_manager',
                'department': 'digital',
            },
            {
                'email': 'test-digital-employee@hahahaproduction.com',
                'first_name': 'Test Digital',
                'last_name': 'Employee',
                'role': 'digital_employee',
                'department': 'digital',
            },
            {
                'email': 'test-sales-manager@hahahaproduction.com',
                'first_name': 'Test Sales',
                'last_name': 'Manager',
                'role': 'sales_manager',
                'department': 'sales',
            },
            {
                'email': 'test-sales-employee@hahahaproduction.com',
                'first_name': 'Test Sales',
                'last_name': 'Employee',
                'role': 'sales_employee',
                'department': 'sales',
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for user_data in test_users:
            email = user_data['email']
            role = user_data['role']
            department = user_data['department']
            # Generate username from email (before @)
            username = email.split('@')[0]

            try:
                # Check if user already exists
                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': user_data['first_name'],
                        'last_name': user_data['last_name'],
                    }
                )

                if not user_created:
                    # Update existing user
                    user.first_name = user_data['first_name']
                    user.last_name = user_data['last_name']
                    user.save()

                # Get or create profile
                profile, profile_created = UserProfile.objects.get_or_create(user=user)

                # Update profile
                profile.role = role
                profile.department = department
                profile.setup_completed = True  # Skip onboarding for test users
                profile.save()

                if user_created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created test user: {email} ({role})')
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated test user: {email} ({role})')
                    )

            except Exception as e:
                skipped_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to create/update {email}: {str(e)}')
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Test Users Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'  Updated: {updated_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.ERROR(f'  Failed: {skipped_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Test users are ready for impersonation!'))
        self.stdout.write(self.style.SUCCESS('Use the Role Impersonator in the frontend to test different roles.'))
