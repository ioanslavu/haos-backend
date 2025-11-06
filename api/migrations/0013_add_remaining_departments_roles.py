# Generated manually on 2025-11-06

from django.db import migrations
from django.contrib.auth.hashers import make_password


def add_departments_roles_and_test_users(apps, schema_editor):
    """
    Add the remaining departments, roles, and test users:
    - Departments: label, marketing, finance, admin, special_operations
    - Roles: manager and employee for each (except special_operations - manager only)
    - Test users for impersonation testing
    """
    Department = apps.get_model('api', 'Department')
    Role = apps.get_model('api', 'Role')
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('api', 'UserProfile')

    # ===== CREATE NEW DEPARTMENTS =====
    print("\n=== Creating additional departments ===")

    label, created = Department.objects.get_or_create(
        code='label',
        defaults={
            'name': 'Label Department',
            'description': 'Record label operations, artist relations, and label management',
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {label.name}")

    marketing, created = Department.objects.get_or_create(
        code='marketing',
        defaults={
            'name': 'Marketing Department',
            'description': 'Marketing campaigns, social media, and promotional activities',
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {marketing.name}")

    finance, created = Department.objects.get_or_create(
        code='finance',
        defaults={
            'name': 'Finance Department',
            'description': 'Financial operations, accounting, and revenue management',
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {finance.name}")

    admin, created = Department.objects.get_or_create(
        code='admin',
        defaults={
            'name': 'Admin Department',
            'description': 'Administrative operations and general management',
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {admin.name}")

    special_ops, created = Department.objects.get_or_create(
        code='special_operations',
        defaults={
            'name': 'Special Operations',
            'description': 'Special projects and executive operations',
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {special_ops.name}")

    # ===== CREATE NEW ROLES =====
    print("\n=== Creating roles for new departments ===")

    # Label roles (employee + manager)
    label_employee, created = Role.objects.get_or_create(
        code='label_employee',
        defaults={
            'name': 'Label Employee',
            'description': 'Label department employee with basic access to own records',
            'level': 200,
            'department': label,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {label_employee.name}")

    label_manager, created = Role.objects.get_or_create(
        code='label_manager',
        defaults={
            'name': 'Label Manager',
            'description': 'Label department manager with full access to department records',
            'level': 300,
            'department': label,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {label_manager.name}")

    # Marketing roles (employee + manager)
    marketing_employee, created = Role.objects.get_or_create(
        code='marketing_employee',
        defaults={
            'name': 'Marketing Employee',
            'description': 'Marketing department employee with basic access to own records',
            'level': 200,
            'department': marketing,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {marketing_employee.name}")

    marketing_manager, created = Role.objects.get_or_create(
        code='marketing_manager',
        defaults={
            'name': 'Marketing Manager',
            'description': 'Marketing department manager with full access to department records',
            'level': 300,
            'department': marketing,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {marketing_manager.name}")

    # Finance roles (employee + manager)
    finance_employee, created = Role.objects.get_or_create(
        code='finance_employee',
        defaults={
            'name': 'Finance Employee',
            'description': 'Finance department employee with basic access to own records',
            'level': 200,
            'department': finance,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {finance_employee.name}")

    finance_manager, created = Role.objects.get_or_create(
        code='finance_manager',
        defaults={
            'name': 'Finance Manager',
            'description': 'Finance department manager with full access to department records',
            'level': 300,
            'department': finance,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {finance_manager.name}")

    # Admin roles (employee + manager)
    admin_employee, created = Role.objects.get_or_create(
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
    if created:
        print(f"✓ Created: {admin_employee.name}")

    admin_manager, created = Role.objects.get_or_create(
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
    if created:
        print(f"✓ Created: {admin_manager.name}")

    # Special Operations role (manager only - no employee role)
    special_ops_manager, created = Role.objects.get_or_create(
        code='special_operations_manager',
        defaults={
            'name': 'Special Operations Manager',
            'description': 'Special operations manager for executive and special projects',
            'level': 300,
            'department': special_ops,
            'is_system_role': True,
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Created: {special_ops_manager.name}")

    # ===== CREATE TEST USERS FOR IMPERSONATION =====
    print("\n=== Creating test users for new departments ===")
    print("NOTE: These users are for the 'Test as Roles' impersonation feature in the UI.")

    # Define test users for new departments
    test_users = [
        # Label department
        {
            'email': 'test.label.manager@hahahaproduction.com',
            'username': 'test_label_mgr',
            'first_name': 'Test Label',
            'last_name': 'Manager',
            'password': 'test123',
            'role': label_manager,
            'department': label,
        },
        {
            'email': 'test.label.employee@hahahaproduction.com',
            'username': 'test_label_emp',
            'first_name': 'Test Label',
            'last_name': 'Employee',
            'password': 'test123',
            'role': label_employee,
            'department': label,
        },
        # Marketing department
        {
            'email': 'test.marketing.manager@hahahaproduction.com',
            'username': 'test_marketing_mgr',
            'first_name': 'Test Marketing',
            'last_name': 'Manager',
            'password': 'test123',
            'role': marketing_manager,
            'department': marketing,
        },
        {
            'email': 'test.marketing.employee@hahahaproduction.com',
            'username': 'test_marketing_emp',
            'first_name': 'Test Marketing',
            'last_name': 'Employee',
            'password': 'test123',
            'role': marketing_employee,
            'department': marketing,
        },
        # Finance department
        {
            'email': 'test.finance.manager@hahahaproduction.com',
            'username': 'test_finance_mgr',
            'first_name': 'Test Finance',
            'last_name': 'Manager',
            'password': 'test123',
            'role': finance_manager,
            'department': finance,
        },
        {
            'email': 'test.finance.employee@hahahaproduction.com',
            'username': 'test_finance_emp',
            'first_name': 'Test Finance',
            'last_name': 'Employee',
            'password': 'test123',
            'role': finance_employee,
            'department': finance,
        },
        # Admin department
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
        # Special Operations (manager only)
        {
            'email': 'test.specialops.manager@hahahaproduction.com',
            'username': 'test_specialops_mgr',
            'first_name': 'Test Special Ops',
            'last_name': 'Manager',
            'password': 'test123',
            'role': special_ops_manager,
            'department': special_ops,
        },
    ]

    # Create test users
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
        if created:
            print(f"  ✓ Created {role.name}: {user.email}")
        else:
            print(f"  → Already exists: {user.email}")

        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': role, 'department': dept, 'setup_completed': True}
        )
        if not profile_created and (profile.role != role or profile.department != dept):
            # Update if exists but with different role/dept
            profile.role = role
            profile.department = dept
            profile.setup_completed = True
            profile.save()
            print(f"  → Updated profile for: {user.email}")

    print("\n=== MIGRATION COMPLETED ===")
    print("\nNew departments added:")
    print("  • Label Department")
    print("  • Marketing Department")
    print("  • Finance Department")
    print("  • Admin Department")
    print("  • Special Operations")
    print("\nNew test users created (password: test123 for all):")
    print("  • test.label.manager@hahahaproduction.com (Label Manager)")
    print("  • test.label.employee@hahahaproduction.com (Label Employee)")
    print("  • test.marketing.manager@hahahaproduction.com (Marketing Manager)")
    print("  • test.marketing.employee@hahahaproduction.com (Marketing Employee)")
    print("  • test.finance.manager@hahahaproduction.com (Finance Manager)")
    print("  • test.finance.employee@hahahaproduction.com (Finance Employee)")
    print("  • test.admin.manager@hahahaproduction.com (Admin Manager)")
    print("  • test.admin.employee@hahahaproduction.com (Admin Employee)")
    print("  • test.specialops.manager@hahahaproduction.com (Special Operations Manager)")
    print("\nAll test users are available in the 'Test as Role' impersonation feature.")
    print("========================================\n")


def reverse_migration(apps, schema_editor):
    """
    Reverse the migration by removing added departments, roles, and test users.
    """
    Department = apps.get_model('api', 'Department')
    Role = apps.get_model('api', 'Role')
    User = apps.get_model('auth', 'User')

    # Delete test users
    test_emails = [
        'test.label.manager@hahahaproduction.com',
        'test.label.employee@hahahaproduction.com',
        'test.marketing.manager@hahahaproduction.com',
        'test.marketing.employee@hahahaproduction.com',
        'test.finance.manager@hahahaproduction.com',
        'test.finance.employee@hahahaproduction.com',
        'test.admin.manager@hahahaproduction.com',
        'test.admin.employee@hahahaproduction.com',
        'test.specialops.manager@hahahaproduction.com',
    ]
    User.objects.filter(email__in=test_emails).delete()

    # Delete roles
    Role.objects.filter(code__in=[
        'label_employee', 'label_manager',
        'marketing_employee', 'marketing_manager',
        'finance_employee', 'finance_manager',
        'admin_employee', 'admin_manager',
        'special_operations_manager',
    ]).delete()

    # Delete departments
    Department.objects.filter(code__in=[
        'label', 'marketing', 'finance', 'admin', 'special_operations'
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_rename_api_userpro_role_9579a2_idx_api_userpro_role_id_4a16d0_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(add_departments_roles_and_test_users, reverse_migration),
    ]
