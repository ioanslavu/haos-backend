#!/usr/bin/env python3
"""
Complete fix for all UserProfile.objects.create patterns.
"""
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    changes_made = False

    while i < len(lines):
        line = lines[i]

        # Check if this line starts a UserProfile.objects.create call
        if 'UserProfile.objects.create(' in line and '=' in line:
            # Extract the variable being assigned
            var_match = re.search(r'(\s+)(self\.\w+|\w+)\s*=\s*UserProfile\.objects\.create\(', line)

            if var_match:
                indent = var_match.group(1)
                var_name = var_match.group(2)

                # Collect all lines of this create() call
                create_lines = [line]
                paren_count = line.count('(') - line.count(')')
                j = i + 1

                while paren_count > 0 and j < len(lines):
                    create_lines.append(lines[j])
                    paren_count += lines[j].count('(') - lines[j].count(')')
                    j += 1

                # Parse the create() call to extract parameters
                full_create = ''.join(create_lines)

                # Extract user= parameter
                user_match = re.search(r'user\s*=\s*([^,\)]+)', full_create)
                dept_match = re.search(r'department\s*=\s*([^,\)]+)', full_create)
                role_match = re.search(r'role\s*=\s*([^,\)]+)', full_create)

                if user_match:
                    user_expr = user_match.group(1).strip()
                    dept_expr = dept_match.group(1).strip() if dept_match else None
                    role_expr = role_match.group(1).strip() if role_match else None

                    # Generate replacement code
                    replacement = f"{indent}{var_name} = {user_expr}.profile\n"
                    if dept_expr:
                        replacement += f"{indent}{var_name}.department = {dept_expr}\n"
                    if role_expr:
                        replacement += f"{indent}{var_name}.role = {role_expr}\n"
                    replacement += f"{indent}{var_name}.save()\n"

                    new_lines.append(replacement)
                    i = j
                    changes_made = True
                    continue

        new_lines.append(line)
        i += 1

    if changes_made:
        with open(filepath, 'w') as f:
            f.writelines(new_lines)
        return True
    return False

# Fix all test files
test_files = [
    'api/tests/test_permissions.py',
    'api/tests/test_viewsets.py',
    'campaigns/tests/test_campaign_viewset_rbac.py',
    'crm_extensions/tests/test_task_viewset_rbac.py',
]

print("Fixing all UserProfile.objects.create() patterns...\n")
for filepath in test_files:
    try:
        if fix_file(filepath):
            print(f"✓ Fixed {filepath}")
        else:
            print(f"- No changes needed for {filepath}")
    except Exception as e:
        print(f"✗ Error fixing {filepath}: {e}")

print("\n✓ Done!")
