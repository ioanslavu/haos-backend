# Generated manually on 2025-11-06

from django.db import migrations


def remove_admin_department(apps, schema_editor):
    """
    Remove the admin department, its roles, and test users.
    This was removed per user request.
    """
    Department = apps.get_model('api', 'Department')
    Role = apps.get_model('api', 'Role')
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('api', 'UserProfile')

    print("\n=== Removing Admin Department ===")

    # First, delete test users with admin roles
    test_admin_emails = [
        'test.admin.manager@hahahaproduction.com',
        'test.admin.employee@hahahaproduction.com',
    ]

    deleted_users = User.objects.filter(email__in=test_admin_emails)
    user_count = deleted_users.count()
    if user_count > 0:
        deleted_users.delete()
        print(f"✓ Deleted {user_count} admin test users")

    # Move any non-test users with admin roles to guest role
    try:
        guest_role = Role.objects.get(code='guest')
        admin_roles = Role.objects.filter(code__in=['admin_manager', 'admin_employee'])

        # Update profiles with admin roles to guest role
        profiles_updated = UserProfile.objects.filter(role__in=admin_roles).exclude(
            user__email__in=test_admin_emails
        ).update(role=guest_role, department=None)

        if profiles_updated > 0:
            print(f"✓ Moved {profiles_updated} user(s) from admin roles to guest role")
    except Role.DoesNotExist:
        print("! Warning: Guest role not found, skipping user migration")

    # Delete admin roles
    roles_deleted = Role.objects.filter(code__in=['admin_manager', 'admin_employee']).delete()
    if roles_deleted[0] > 0:
        print(f"✓ Deleted admin roles: admin_manager, admin_employee")

    # Delete admin department
    dept_deleted = Department.objects.filter(code='admin').delete()
    if dept_deleted[0] > 0:
        print(f"✓ Deleted admin department")

    print("=== Admin Department Removal Complete ===\n")


def restore_admin_department(apps, schema_editor):
    """
    Restore the admin department and roles (reverse migration).
    """
    Department = apps.get_model('api', 'Department')
    Role = apps.get_model('api', 'Role')
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('api', 'UserProfile')
    from django.contrib.auth.hashers import make_password

    # Recreate admin department
    admin, _ = Department.objects.get_or_create(
        code='admin',
        defaults={
            'name': 'Admin Department',
            'description': 'Administrative operations and general management',
            'is_active': True,
        }
    )

    # Recreate admin roles
    admin_employee, _ = Role.objects.get_or_create(
        code='admin_employee',
        defaults={
            'name': 'Admin Employee',
            'description': 'Admin department employee with basic access to own records',
            'level': 200,
            'department': admin,
            'is_system_role': True,
            'is_active': True,
        }
    )

    admin_manager, _ = Role.objects.get_or_create(
        code='admin_manager',
        defaults={
            'name': 'Admin Manager',
            'description': 'Admin department manager with full access to department records',
            'level': 300,
            'department': admin,
            'is_system_role': True,
            'is_active': True,
        }
    )

    # Recreate test users
    test_users = [
        {
            'email': 'test.admin.manager@hahahaproduction.com',
            'username': 'test_admin_mgr',
            'first_name': 'Test Admin',
            'last_name': 'Manager',
            'password': 'test123',
            'role': admin_manager,
            'department': admin,
        },
        {
            'email': 'test.admin.employee@hahahaproduction.com',
            'username': 'test_admin_emp',
            'first_name': 'Test Admin',
            'last_name': 'Employee',
            'password': 'test123',
            'role': admin_employee,
            'department': admin,
        },
    ]

    for user_data in test_users:
        role = user_data.pop('role')
        dept = user_data.pop('department')
        password = user_data.pop('password')

        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                **user_data,
                'password': make_password(password),
                'is_active': True,
            }
        )

        UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': role, 'department': dept, 'setup_completed': True}
        )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_alter_departmentrequest_requested_department'),
    ]

    operations = [
        migrations.RunPython(remove_admin_department, restore_admin_department),
    ]
