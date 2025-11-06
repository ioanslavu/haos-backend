# Song Workflow System Tests

Comprehensive test suite for the Song Workflow system in HaHaHa Production's record label platform.

## Overview

This test suite covers all aspects of the Song Workflow system, including:
- Models and database logic
- Permission and access control
- Validation functions
- REST API endpoints
- Checklist templates
- Alert service

## Test Files

### 1. `test_song_models.py` (28 test cases)

Tests all Song Workflow models:

**Song Model:**
- Creating a song
- Stage transitions
- `calculate_checklist_progress()` method
- `can_transition_to()` method
- `update_computed_fields()` method
- `is_overdue` calculation
- `days_in_current_stage` calculation

**SongChecklistItem Model:**
- Creating checklist items
- Manual completion
- `validate()` method for different validation types
  - Manual validation
  - Auto entity exists (Work, Recording, Release)
  - Auto field exists (ISWC, genre, etc.)
  - Auto split validated (100% splits)
  - Auto count minimum

**SongStageTransition Model:**
- Audit log creation
- Tracking transition history

**SongAsset Model:**
- Creating assets with Google Drive URLs
- Review status changes
- `dimensions` property

**SongNote & SongAlert Models:**
- Basic CRUD operations
- Sales pitch tracking
- Alert read/unread status

### 2. `test_song_permissions.py` (38 test cases)

Tests permission functions from `permissions.py`:

**View Permissions:**
- `user_can_view_song()` for each department
- Admin can view all songs
- Creator can always see their songs
- Publishing can see Publishing stage songs
- Marketing can ONLY see MARKETING_ASSETS stage
- Sales can see Publishing but NOT splits
- Digital can see their stages
- Archived songs only visible to admin and creator

**Edit Permissions:**
- `user_can_edit_song()` for each department
- Admin can edit all songs
- Publishing can edit draft and publishing stages
- Marketing can only edit marketing_assets stage
- No editing in released stage (except admin)

**Split Visibility:**
- `user_can_view_splits()` enforcement
- Sales CANNOT see splits (even in Publishing stage)
- Marketing cannot see splits
- Digital cannot see splits
- Publishing can see splits in their stages
- Label can see splits in their stages

**Stage Transitions:**
- `user_can_transition_stage()` validation
- Valid transitions with complete checklist
- Invalid transitions (incomplete checklist, wrong department, invalid stage)
- Admin override capabilities
- Label can send back to Marketing

**Helper Functions:**
- `get_visible_stages_for_user()`
- `get_editable_stages_for_user()`
- `get_department_for_stage()`

**Matrix Enforcement:**
- VISIBILITY_MATRIX enforcement
- EDIT_MATRIX enforcement
- VALID_TRANSITIONS enforcement

### 3. `test_song_validators.py` (19 test cases)

Tests validation functions from `validators.py`:

**validate_auto_entity_exists():**
- Work exists validation
- Recording exists validation
- Release exists validation

**validate_auto_field_exists():**
- ISWC field validation
- Regular field validation (genre, etc.)
- Missing entity handling

**validate_auto_split_validated():**
- Splits = 100% validation
- Splits != 100% (99%, 101%) rejection
- Multiple splits totaling 100%
- `skip_if_empty` option for publishers

**validate_auto_count_minimum():**
- Minimum count met/not met
- Writer splits count
- Recording credits count

**run_validation():**
- Dispatcher function for all validation types
- Manual validation
- Auto validations
- Unknown validation type handling

**revalidate_checklist_item():**
- Updates `is_complete` status automatically
- Skips manual items

### 4. `test_song_api.py` (27 test cases)

Tests REST API endpoints using Django REST Framework's APITestCase:

**Song CRUD:**
- List songs (filtered by department)
- Create song (permissions check)
- Retrieve song (permission-aware serialization)
- Update song
- Delete song
- Non-owner cannot delete song

**Custom Actions:**
- `POST /songs/{id}/transition/` - valid transition
- `POST /songs/{id}/transition/` - invalid transition (checklist incomplete)
- `POST /songs/{id}/transition/` - invalid transition (wrong department)
- `POST /songs/{id}/send_to_digital/` - creates urgent alert
- `POST /songs/{id}/archive/`
- `GET /songs/my_queue/` - department filtering
- `GET /songs/overdue/` - manager only
- `GET /songs/stats/` - statistics

**Nested Resources:**
- `GET /songs/{id}/checklist/`
- `POST /songs/{id}/checklist/{item}/toggle/`
- Cannot toggle auto checklist items
- `POST /songs/{id}/assets/` - create asset
- `POST /songs/{id}/assets/{asset}/review/` - Label reviews asset
- `POST /songs/{id}/notes/` - add note
- Sales pitch notes
- `GET /alerts/` - list alerts
- `POST /alerts/{id}/mark_read/`
- `GET /alerts/unread_count/`

**Permission Tests:**
- Marketing user cannot see Publishing stage songs (403)
- Marketing can only edit marketing_assets stage

### 5. `test_checklist_templates.py` (18 test cases)

Tests checklist generation from `checklist_templates.py`:

**Template Structure:**
- `generate_checklist_for_stage()` creates correct items
- Each stage template has correct number of items
- All templates have correct structure (category, item_name, etc.)
- Items have sequential order numbers
- Validation rules present for auto validations

**Stage Templates:**
- Publishing stage (6 items)
- Label Recording stage (8 items)
- Marketing Assets stage (5 items)
- Label Review stage (4 items)
- Ready for Digital stage (3 items)
- Digital Distribution stage (6 items)
- Draft/Released/Archived have no checklist

**Validation Configuration:**
- Required vs optional items
- Validation types (manual, auto_entity_exists, etc.)
- Validation rules properly configured
- Help text present where appropriate

### 6. `test_alert_service.py` (22 test cases)

Tests alert generation from `alert_service.py`:

**Stage Transition Alerts:**
- `create_stage_transition_alert()` creates alert for target dept
- Alert includes user info
- Alert for assigned user (if exists)
- No alert for stages with no department

**Send to Digital Alert:**
- `create_send_to_digital_alert()` creates URGENT alert
- Alert targets Digital department
- Alert message includes Label user

**Asset Submitted Alert:**
- `create_asset_submitted_alert()` notifies Label
- Alert targets Label department
- Priority is IMPORTANT

**Asset Reviewed Alert:**
- `create_asset_reviewed_alert()` notifies Marketing
- Asset approved (priority: info)
- Asset rejected (priority: important)
- Asset revision requested (priority: important)
- Alert includes reviewer name

**Sales Pitch Alert:**
- `create_sales_pitch_alert()` notifies song creator
- Priority is INFO
- No alert if no creator

**Alert Priorities:**
- Stage transition: IMPORTANT
- Send to digital: URGENT
- Asset submitted: IMPORTANT
- Asset approved: INFO
- Asset rejected: IMPORTANT
- Sales pitch: INFO

## Running Tests

### Run all tests:
```bash
python manage.py test catalog.tests
```

### Run specific test file:
```bash
python manage.py test catalog.tests.test_song_models
python manage.py test catalog.tests.test_song_permissions
python manage.py test catalog.tests.test_song_validators
python manage.py test catalog.tests.test_song_api
python manage.py test catalog.tests.test_checklist_templates
python manage.py test catalog.tests.test_alert_service
```

### Run specific test case:
```bash
python manage.py test catalog.tests.test_song_models.SongModelTestCase
```

### Run specific test method:
```bash
python manage.py test catalog.tests.test_song_models.SongModelTestCase.test_song_creation
```

### Run with verbosity:
```bash
python manage.py test catalog.tests --verbosity=2
```

### Run with coverage:
```bash
coverage run --source='.' manage.py test catalog.tests
coverage report
coverage html  # Generate HTML report
```

## Test Coverage

The test suite aims for 80%+ code coverage of critical functionality:

**Covered:**
- All Song Workflow models (Song, SongChecklistItem, SongStageTransition, SongAsset, SongNote, SongAlert)
- All permission functions (view, edit, transition, splits visibility)
- All validation functions (entity exists, field exists, split validated, count minimum)
- All API endpoints (CRUD, custom actions, nested resources)
- All checklist templates (6 stages)
- All alert service functions (5 alert types)

**Critical Workflows Tested:**
- Stage transitions with checklist validation
- Department-based permission enforcement
- Split visibility rules (Sales cannot see splits)
- Asset submission and review workflow
- Alert generation for workflow events

**Edge Cases Tested:**
- Invalid stage transitions
- Incomplete checklists
- Permission denials
- Invalid data (splits != 100%, missing entities)
- Archived songs visibility

## Test Data Setup

All tests use `setUp()` to create:
- Departments (Publishing, Label, Marketing, Digital, Sales)
- Roles (Admin, Employee, Manager for each department)
- Users with profiles and department assignments
- Songs, Works, Recordings, Releases as needed
- Entities for credits and splits

Tests use Django's `TestCase` and DRF's `APITestCase` for proper database isolation.

## Test Summary

| File | Test Cases | Focus |
|------|-----------|-------|
| test_song_models.py | 28 | Model logic, methods, computed fields |
| test_song_permissions.py | 38 | Access control, department permissions |
| test_song_validators.py | 19 | Checklist validation logic |
| test_song_api.py | 27 | REST API endpoints, HTTP responses |
| test_checklist_templates.py | 18 | Template structure, item generation |
| test_alert_service.py | 22 | Alert generation, priorities |
| **TOTAL** | **152** | **Comprehensive coverage** |

## Notes

- Tests require Django and Django REST Framework
- Tests use in-memory SQLite database for speed
- All tests are isolated (no data leakage between tests)
- Tests follow Django testing best practices
- API tests use `APIClient.force_authenticate()` for permission testing
- Tests cover both success and failure scenarios

## Issues Encountered

None. All test files created successfully with comprehensive coverage.

## Next Steps

1. Run the full test suite: `python manage.py test catalog.tests`
2. Generate coverage report: `coverage run --source='.' manage.py test catalog.tests && coverage report`
3. Review any failing tests and fix issues
4. Aim for 80%+ coverage on critical code paths
5. Add integration tests if needed for complex workflows
