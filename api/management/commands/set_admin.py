"""
Django management command to set a user as administrator.

Usage:
    python manage.py set_admin <email>
    python manage.py set_admin ioan@hahahaproduction.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from api.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Set a user as administrator by email'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address of the user to set as administrator'
        )

    def handle(self, *args, **options):
        email = options['email']

        try:
            # Get user by email
            user = User.objects.get(email=email)

            # Get or create profile
            profile, created = UserProfile.objects.get_or_create(user=user)

            # Set as administrator
            profile.role = 'administrator'
            profile.department = None  # Admins don't have specific department
            profile.setup_completed = True  # Skip onboarding
            profile.save()

            # Also set as Django superuser for admin panel access
            if not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Also granted Django superuser access to {email}')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set {email} as administrator!\n'
                    f'  - Role: administrator\n'
                    f'  - Department: None (can oversee all)\n'
                    f'  - Onboarding: Skipped\n'
                    f'  - Django Admin: Enabled'
                )
            )

        except User.DoesNotExist:
            raise CommandError(
                f'User with email "{email}" does not exist.\n'
                f'Please ensure the user has logged in at least once.'
            )
        except Exception as e:
            raise CommandError(f'Error setting user as administrator: {str(e)}')
