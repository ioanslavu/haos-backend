#!/bin/bash
#
# Set a user as administrator in the HaOS system.
# Works with the new Role model hierarchy.
#
# Usage:
#   ./scripts/set-admin.sh <email>
#
# Example:
#   ./scripts/set-admin.sh ioan.slavu@hahahaproduction.com
#

set -e

# Check if email argument is provided
if [ -z "$1" ]; then
    echo "❌ Error: Email address required"
    echo ""
    echo "Usage: $0 <email>"
    echo "Example: $0 ioan.slavu@hahahaproduction.com"
    exit 1
fi

EMAIL="$1"

echo "=========================================="
echo "Setting $EMAIL as Administrator"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from the backend directory."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Create Python script to set admin
cat > /tmp/set_admin_temp.py << 'PYTHON_SCRIPT'
import sys
from django.contrib.auth import get_user_model
from api.models import UserProfile, Role

User = get_user_model()

email = sys.argv[1]

try:
    # Find user by email
    user = User.objects.get(email=email)
    print(f"✓ Found user: {user.email}")

    # Get administrator role
    admin_role = Role.objects.get(code='administrator')
    print(f"✓ Found admin role: {admin_role.name} (level {admin_role.level})")

    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)

    if created:
        print(f"✓ Created new profile for {user.email}")
    else:
        print(f"✓ Found existing profile")
        if profile.role:
            print(f"  Current role: {profile.role.name} (level {profile.role.level})")
        if profile.department:
            print(f"  Current department: {profile.department.name}")

    # Update to admin role (admins don't need department)
    old_role = profile.role.name if profile.role else 'None'
    profile.role = admin_role
    profile.department = None  # Admins don't have department
    profile.save()

    print("")
    print("========================================")
    print("✅ SUCCESS!")
    print("========================================")
    print(f"User: {user.email}")
    print(f"Role changed: {old_role} → {admin_role.name}")
    print(f"Role level: {admin_role.level}")
    print(f"Department: None (admins have cross-department access)")
    print(f"Is Admin: {profile.is_admin}")
    print(f"Is Manager: {profile.is_manager}")
    print("")
    print("The user now has full administrator privileges.")
    print("========================================")

except User.DoesNotExist:
    print(f"❌ ERROR: User with email '{email}' not found")
    print("")
    print("Available users:")
    for u in User.objects.all().order_by('email'):
        print(f"  - {u.email}")
    sys.exit(1)
except Role.DoesNotExist:
    print("❌ ERROR: Administrator role not found in database")
    print("")
    print("Available roles:")
    for r in Role.objects.all().order_by('-level'):
        print(f"  - {r.code}: {r.name} (level {r.level})")
    print("")
    print("Please run migrations first: python manage.py migrate")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

# Run the Python script through Django shell
python manage.py shell << EOF
import sys
sys.argv = ['', '$EMAIL']
exec(open('/tmp/set_admin_temp.py').read())
EOF

# Clean up temp file
rm -f /tmp/set_admin_temp.py

echo ""
echo "Done! The user can now access all admin features."
