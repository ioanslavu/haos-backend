#!/usr/bin/env python3
"""
Comprehensive fix for UserProfile creation in tests.
Converts UserProfile.objects.create() to use auto-created profiles.
"""
import re

def fix_userprofile_creates(filepath):
    """Fix all UserProfile.objects.create calls in a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Pattern: var_name = UserProfile.objects.create(user=user_var, department=dept_var, role=role_expr)
    # We need to handle multi-line creates

    # First, let's handle single-line creates
    pattern = r'(\s+)(\w+)\s*=\s*UserProfile\.objects\.create\(\s*user=(\w+),\s*department=([^,]+),\s*role=([^)]+)\)'

    def replace_single_line(match):
        indent = match.group(1)
        var_name = match.group(2)
        user_var = match.group(3)
        dept_expr = match.group(4).strip()
        role_expr = match.group(5).strip()

        return f'''{indent}{var_name} = {user_var}.profile
{indent}{var_name}.department = {dept_expr}
{indent}{var_name}.role = {role_expr}
{indent}{var_name}.save()'''

    content = re.sub(pattern, replace_single_line, content)

    # Now handle multi-line creates (where parameters are on separate lines)
    # Pattern: var = UserProfile.objects.create(\n    user=...,\n    department=...,\n    role=...\n)
    pattern_multiline = r'(\s+)(\w+)\s*=\s*UserProfile\.objects\.create\(\s*\n\s+user=(\w+),\s*\n\s+department=([^,\n]+),\s*\n\s+role=([^)\n]+)\s*\)'

    def replace_multi_line(match):
        indent = match.group(1)
        var_name = match.group(2)
        user_var = match.group(3)
        dept_expr = match.group(4).strip()
        role_expr = match.group(5).strip()

        return f'''{indent}{var_name} = {user_var}.profile
{indent}{var_name}.department = {dept_expr}
{indent}{var_name}.role = {role_expr}
{indent}{var_name}.save()'''

    content = re.sub(pattern_multiline, replace_multi_line, content)

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

# Fix all test files
test_files = [
    'api/tests/test_permissions.py',
    'api/tests/test_viewsets.py',
    'campaigns/tests/test_campaign_viewset_rbac.py',
    'crm_extensions/tests/test_task_viewset_rbac.py',
]

print("Fixing UserProfile.objects.create() calls...\n")
for filepath in test_files:
    if fix_userprofile_creates(filepath):
        print(f"✓ Fixed {filepath}")
    else:
        print(f"- No changes for {filepath}")

print("\n✓ Done!")
