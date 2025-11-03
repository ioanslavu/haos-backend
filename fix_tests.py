#!/usr/bin/env python3
"""
Script to fix test files to use Role and Department FK instances instead of strings.
"""
import re
import sys

# Test files to fix
test_files = [
    'api/tests/test_permissions.py',
    'api/tests/test_viewsets.py',
    'campaigns/tests/test_campaign_viewset_rbac.py',
    'crm_extensions/tests/test_task_viewset_rbac.py',
]

def fix_test_file(filepath):
    """Fix a single test file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Warning: {filepath} not found, skipping...")
        return

    original_content = content

    # 1. Add Role import if not present
    if 'from api.models import' in content and 'Role' not in content:
        content = content.replace(
            'from api.models import Department, UserProfile',
            'from api.models import Department, Role, UserProfile'
        )
        content = content.replace(
            'from api.models import Department,',
            'from api.models import Department, Role,'
        )

    # 2. Replace role='string' with role=Role.objects.get(code='string')
    # Map old role strings to new role codes
    role_mapping = {
        "'employee'": "Role.objects.get(code='digital_employee')",
        "'manager'": "Role.objects.get(code='digital_manager')",
        "'administrator'": "Role.objects.get(code='administrator')",
        "'admin'": "Role.objects.get(code='administrator')",
        "'guest'": "Role.objects.get(code='guest')",
    }

    for old_role, new_role in role_mapping.items():
        # Replace role=<string> patterns
        pattern = r"role=" + old_role
        content = re.sub(pattern, f"role={new_role}", content)

    # 3. Save if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {filepath}")
    else:
        print(f"- No changes needed for {filepath}")

if __name__ == '__main__':
    print("Fixing test files to use Role/Department FKs...\n")
    for test_file in test_files:
        fix_test_file(test_file)
    print("\n✓ All test files fixed!")
