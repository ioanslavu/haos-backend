#!/usr/bin/env python3
"""Fix test files to use get_or_create for Department and Role."""
import re

test_files = [
    'api/tests/test_permissions.py',
    'api/tests/test_viewsets.py',
    'campaigns/tests/test_campaign_viewset_rbac.py',
    'crm_extensions/tests/test_task_viewset_rbac.py',
]

for filepath in test_files:
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Replace Department.objects.create with get_or_create
    content = re.sub(
        r'Department\.objects\.create\(',
        'Department.objects.get_or_create(',
        content
    )

    # For get_or_create, we need to add [0] to get the object
    # Find patterns like: var = Department.objects.get_or_create(name=..., code=...)
    # and add [0] at the end if not already there
    content = re.sub(
        r'(\w+)\s*=\s*Department\.objects\.get_or_create\(([^)]+)\)(?!\[0\])',
        r'\1, _ = Department.objects.get_or_create(\2)',
        content
    )

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {filepath}")
    else:
        print(f"- No changes for {filepath}")
