#!/usr/bin/env python3
"""
Fix Campaign test fixtures to match actual Campaign model.
Changes:
1. title -> campaign_name
2. Add brand=client (reuse client entity as brand for tests)
"""
import re

filepath = 'campaigns/tests/test_campaign_viewset_rbac.py'

with open(filepath, 'r') as f:
    content = f.read()

# Replace title= with campaign_name=
content = content.replace("title='", "campaign_name='")
content = content.replace('title="', 'campaign_name="')

# For each Campaign.objects.create, add brand=client if not present
# Pattern: Campaign.objects.create(...client=X...)
# We need to add brand=X after client=X

def add_brand_field(match):
    """Add brand field to Campaign.objects.create if not present."""
    full_match = match.group(0)

    # Check if brand is already specified
    if 'brand=' in full_match:
        return full_match

    # Find client= assignment
    client_match = re.search(r'client=([^,\)]+)', full_match)
    if not client_match:
        return full_match  # No client field found, skip

    client_value = client_match.group(1).strip()

    # Add brand field after client field
    result = full_match.replace(
        f'client={client_value}',
        f'client={client_value},\n            brand={client_value}'
    )

    return result

# Match Campaign.objects.create(...) including multiline
pattern = r'Campaign\.objects\.create\([^)]*\)'
content = re.sub(pattern, add_brand_field, content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)

print("✓ Fixed Campaign test fixtures")
