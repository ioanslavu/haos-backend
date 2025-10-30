# Role Impersonation (Test as Roles) Setup

## Overview
The impersonation system allows administrators to test the application with different role permissions without logging out. This is implemented using test users with the `test.` email prefix.

## Test Users

All test users use the password: `test123`

| Email | Role | Department | Level |
|-------|------|------------|-------|
| test.admin@hahahaproduction.com | Administrator | None | 1000 |
| test.digital.manager@hahahaproduction.com | Digital Manager | Digital | 300 |
| test.digital.employee@hahahaproduction.com | Digital Employee | Digital | 200 |
| test.sales.manager@hahahaproduction.com | Sales Manager | Sales | 300 |
| test.sales.employee@hahahaproduction.com | Sales Employee | Sales | 200 |
| test.publishing.manager@hahahaproduction.com | Publishing Manager | Publishing | 300 |
| test.publishing.employee@hahahaproduction.com | Publishing Employee | Publishing | 200 |
| test.guest@hahahaproduction.com | Guest | None | 100 |

## API Endpoints

### Get Test Users (Admin Only)
```
GET /api/v1/impersonate/test-users/
```

Returns list of test users sorted by role level (highest first).

**Response:**
```json
{
  "test_users": [
    {
      "id": 123,
      "email": "test.admin@hahahaproduction.com",
      "first_name": "Test Admin",
      "last_name": "User",
      "full_name": "Test Admin User",
      "role": {
        "code": "administrator",
        "name": "Administrator",
        "level": 1000
      },
      "department": null
    }
    // ... more users
  ],
  "count": 8
}
```

### Start Impersonation
```
POST /api/v1/impersonate/start/
Body: { "user_id": 123 }
```

Starts impersonation session. Stores `_impersonate` key in session.

### Stop Impersonation
```
POST /api/v1/impersonate/stop/
```

Stops impersonation and returns to real user.

### Check Impersonation Status
```
GET /api/v1/impersonate/status/
```

Returns current impersonation status.

## How It Works

1. **Session-Based**: Impersonation is stored in Django session with key `_impersonate`
2. **Admin Only**: Only users with administrator role (level ≥ 1000) can impersonate
3. **Test Users Only**: Frontend filters for users with email starting with `test.`
4. **Full Session Switch**: When impersonating, all API calls are made as the test user

## Frontend Integration

### RoleImpersonator Component
Location: `frontend/src/components/layout/RoleImpersonator.tsx`

- Fetches test users from `/api/v1/impersonate/test-users/`
- Displays dropdown with all test users sorted by role level
- Shows "Test as Role" button for admins
- Handles start/stop impersonation

### ImpersonationBanner Component
Location: `frontend/src/components/layout/ImpersonationBanner.tsx`

- Shows amber banner at top when impersonating
- Displays current test user name and role
- Quick "Stop Testing" button

## Identifying Test Users

Test users can be identified by:
- Email starts with `test.` (e.g., `test.admin@hahahaproduction.com`)
- Always from `@hahahaproduction.com` domain
- Have clear role names in first_name field (e.g., "Test Admin")

## Security

- ✅ Only administrators can start impersonation
- ✅ Only test users can be impersonated
- ✅ Real user accounts cannot be impersonated
- ✅ Session-based with server-side validation
- ✅ Clear visual indicators when testing (banner, button state)

## Creating New Test Users

To add a new test user:

1. Use Django shell:
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from api.models import UserProfile, Role, Department

User = get_user_model()

# Get role and department
role = Role.objects.get(code='digital_employee')
dept = Department.objects.get(code='digital')

# Create user
user = User.objects.create(
    email='test.newuser@hahahaproduction.com',
    username='test.newuser@hahahaproduction.com',
    first_name='Test New',
    last_name='User',
    password=make_password('test123'),
    is_active=True
)

# Create profile
UserProfile.objects.create(
    user=user,
    role=role,
    department=dept
)
```

2. User will automatically appear in impersonation dropdown

## Troubleshooting

### "No test users found" in dropdown
- Check that test users exist: `User.objects.filter(email__startswith='test.')`
- Verify users have profiles: `user.profile` should exist
- Check user is admin: only admins see the dropdown

### Impersonation not working
- Check session middleware is enabled
- Verify `_impersonate` key in session
- Check CSRF token is being sent with requests

### Test users can't login directly
- This is intentional - test users are for impersonation only
- Only OAuth users should login directly
- Test users exist solely for role testing via impersonation
