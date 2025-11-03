#!/usr/bin/env python3
"""
Script to fix test files to use auto-created UserProfile instead of creating duplicates.
"""
import re

test_files = [
    'api/tests/test_permissions.py',
    'api/tests/test_viewsets.py',
    'campaigns/tests/test_campaign_viewset_rbac.py',
    'crm_extensions/tests/test_task_viewset_rbac.py',
]

def fix_profile_creation(filepath):
    """Fix UserProfile.objects.create() to get auto-created profile and update it."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line creates a UserProfile
        if 'UserProfile.objects.create(' in line and 'user=' in line:
            # Capture the variable name
            var_match = re.search(r'(\w+)\s*=\s*UserProfile\.objects\.create\(', line)
            if var_match:
                var_name = var_match.group(1)

                # Find the closing parenthesis for this create() call
                create_block = line
                paren_count = line.count('(') - line.count(')')
                j = i + 1
                while paren_count > 0 and j < len(lines):
                    create_block += lines[j]
                    paren_count += lines[j].count('(') - lines[j].count(')')
                    j += 1

                # Extract user variable and other parameters
                user_match = re.search(r'user=([^,\)]+)', create_block)
                dept_match = re.search(r'department=([^,\)]+)', create_block)
                role_match = re.search(r'role=([^,\)]+)', create_block)

                if user_match:
                    user_var = user_match.group(1).strip()

                    # Generate replacement code
                    indent = re.match(r'(\s*)', line).group(1)
                    replacement = f"{indent}{var_name} = {user_var}.profile\n"
                    if dept_match:
                        dept_var = dept_match.group(1).strip()
                        replacement += f"{indent}{var_name}.department = {dept_var}\n"
                    if role_match:
                        role_var = role_match.group(1).strip()
                        replacement += f"{indent}{var_name}.role = {role_var}\n"
                    replacement += f"{indent}{var_name}.save()\n"

                    new_lines.append(replacement)
                    i = j
                    continue

        new_lines.append(line)
        i += 1

    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    print(f"✓ Fixed profile creation in {filepath}")

if __name__ == '__main__':
    print("Fixing UserProfile creation in test files...\n")
    for test_file in test_files:
        try:
            fix_profile_creation(test_file)
        except Exception as e:
            print(f"✗ Error fixing {test_file}: {e}")
    print("\n✓ Done!")
