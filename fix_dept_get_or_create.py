#!/usr/bin/env python3
"""
Fix Department.objects.get_or_create to use proper defaults parameter.
This prevents trying to create departments with same code but different names.
"""
import re

test_files = [
    'api/tests/test_permissions.py',
    'api/tests/test_viewsets.py',
    'campaigns/tests/test_campaign_viewset_rbac.py',
    'crm_extensions/tests/test_task_viewset_rbac.py',
]

def fix_dept_get_or_create(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Pattern: Department.objects.get_or_create(name='...', code='...')
    # Replace with: Department.objects.get_or_create(code='...', defaults={'name': '...'})

    pattern = r"Department\.objects\.get_or_create\(name='([^']+)',\s*code='([^']+)'\)"

    def replacement(match):
        name = match.group(1)
        code = match.group(2)
        return f"Department.objects.get_or_create(code='{code}', defaults={{'name': '{name}'}})"

    content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

print("Fixing Department.objects.get_or_create calls...\n")
for filepath in test_files:
    if fix_dept_get_or_create(filepath):
        print(f"✓ Fixed {filepath}")
    else:
        print(f"- No changes for {filepath}")

print("\n✓ Done!")
