# Song Workflow Testing Guide

**Version:** 1.0
**Last Updated:** 2025-11-06
**Status:** Ready for Testing

---

## Overview

This guide provides step-by-step instructions to test the complete Song Workflow system end-to-end, from DRAFT to RELEASED.

---

## Prerequisites

### Test Users Required

You need users from each department with appropriate permissions:

| Department | User Email | Role Level | Notes |
|------------|-----------|------------|-------|
| Publishing | `publishing@test.com` | 100+ | Can create songs, add works |
| Label | `label@test.com` | 100+ | Manages recordings, reviews assets |
| Marketing | `marketing@test.com` | 100+ | Uploads marketing assets |
| Digital | `digital@test.com` | 100+ | Creates releases, distributes |
| Sales | `sales@test.com` | 100+ | Read-only, can add notes |
| Admin | `admin@test.com` | 1000+ | Full access to everything |

### Test Data Required

- **Artist Entity**: Create an artist (e.g., "Test Artist")
- **Writer Entity**: Create a writer/composer (e.g., "John Writer")
- **Producer Entity**: Create a producer (e.g., "Jane Producer")
- **Master Audio File**: Prepare a WAV/FLAC file for upload
- **Cover Artwork**: Prepare a 3000x3000px JPG/PNG image

---

## Test Workflow: Complete Song Lifecycle

### Stage 1: DRAFT → PUBLISHING

**Logged in as**: `publishing@test.com`

#### Step 1.1: Create New Song
```http
POST /api/songs/
Content-Type: application/json

{
  "title": "Test Song Alpha",
  "artist": <artist_id>,
  "genre": "Pop",
  "language": "en",
  "priority": "normal",
  "target_release_date": "2025-12-01"
}
```

**Expected Result**:
- ✅ Song created with `stage="draft"`
- ✅ `created_by` = current user
- ✅ Response includes full song details

#### Step 1.2: Transition to Publishing
```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "publishing",
  "notes": "Moving to publishing department"
}
```

**Expected Result**:
- ✅ Song `stage="publishing"`
- ✅ Checklist generated with 6 items (Work Setup, Writer Splits, Legal)
- ✅ Alert created for Publishing department
- ✅ `stage_entered_at` updated
- ✅ `assigned_department` = Publishing

**Verify Checklist**:
```http
GET /api/songs/<song_id>/checklist/
```

**Expected Checklist Items**:
- [ ] Work entity created
- [ ] ISWC assigned
- [ ] At least 1 writer added
- [ ] Writer splits = 100%
- [ ] Publisher splits = 100% (if publishers exist)
- [ ] Publishing agreements uploaded

---

### Stage 2: PUBLISHING (Complete Checklist)

**Logged in as**: `publishing@test.com`

#### Step 2.1: Create Work
```http
POST /api/works/
Content-Type: application/json

{
  "title": "Test Song Alpha",
  "type": "musical_work",
  "language": "en"
}
```

#### Step 2.2: Link Work to Song
```http
PATCH /api/songs/<song_id>/
Content-Type: application/json

{
  "work": <work_id>
}
```

**Check Checklist**:
- ✅ "Work entity created" should auto-complete

#### Step 2.3: Add ISWC to Work
```http
POST /api/works/<work_id>/add_iswc/
Content-Type: application/json

{
  "iswc": "T-123.456.789-0"
}
```

**Check Checklist**:
- ✅ "ISWC assigned" should auto-complete

#### Step 2.4: Add Writer Split
```http
POST /api/splits/
Content-Type: application/json

{
  "scope": "work",
  "object_id": <work_id>,
  "right_type": "writer",
  "entity": <writer_entity_id>,
  "share": "100.00"
}
```

**Check Checklist**:
- ✅ "At least 1 writer added" should auto-complete
- ✅ "Writer splits = 100%" should auto-complete

#### Step 2.5: Mark Manual Items Complete
```http
POST /api/songs/<song_id>/checklist/<item_id>/toggle/
```

Complete manually:
- [ ] Publishing agreements uploaded

**Verify Checklist Progress**:
```http
GET /api/songs/<song_id>/
```

**Expected**:
- ✅ `checklist_progress` = 100.00

---

### Stage 3: PUBLISHING → LABEL_RECORDING

**Logged in as**: `publishing@test.com`

```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "label_recording",
  "notes": "Ready for recording"
}
```

**Expected Result**:
- ✅ Song `stage="label_recording"`
- ✅ New checklist generated with 8 items (Recording Setup, Audio Files, Credits, Master Rights, Legal)
- ✅ Alert created for Label department
- ✅ `assigned_department` = Label

**Verify Checklist**:
```http
GET /api/songs/<song_id>/checklist/
```

**Expected Checklist Items**:
- [ ] Recording entity created
- [ ] ISRC assigned
- [ ] Master audio uploaded
- [ ] Instrumental uploaded (optional)
- [ ] At least 1 credit added
- [ ] Master splits = 100%
- [ ] Production contracts uploaded
- [ ] Master rights cleared

---

### Stage 4: LABEL_RECORDING (Complete Checklist)

**Logged in as**: `label@test.com`

#### Step 4.1: Create Recording
```http
POST /api/recordings/
Content-Type: application/json

{
  "title": "Test Song Alpha",
  "work": <work_id>,
  "duration": "00:03:45",
  "language": "en"
}
```

#### Step 4.2: Link Recording to Song
```http
POST /api/songs/<song_id>/recordings/add/
Content-Type: application/json

{
  "recording_id": <recording_id>
}
```

**Note**: Since Song.recordings is M2M, you may need a custom endpoint or use:
```python
# Via Django shell or custom endpoint
song.recordings.add(recording)
```

**Check Checklist**:
- ✅ "Recording entity created" should auto-complete

#### Step 4.3: Add ISRC to Recording
```http
POST /api/recordings/<recording_id>/add_isrc/
Content-Type: application/json

{
  "isrc": "USXXX2500001"
}
```

**Check Checklist**:
- ✅ "ISRC assigned" should auto-complete

#### Step 4.4: Upload Master Audio
```http
POST /api/assets/
Content-Type: multipart/form-data

scope=recording
object_id=<recording_id>
kind=audio_wav
file=<master_audio.wav>
is_master=true
```

**Check Checklist**:
- ✅ "Master audio uploaded" should auto-complete

#### Step 4.5: Add Producer Credit
```http
POST /api/credits/
Content-Type: application/json

{
  "scope": "recording",
  "object_id": <recording_id>,
  "entity": <producer_entity_id>,
  "role": "producer",
  "is_featured": false
}
```

**Check Checklist**:
- ✅ "At least 1 credit added" should auto-complete

#### Step 4.6: Add Master Splits
```http
POST /api/splits/
Content-Type: application/json

{
  "scope": "recording",
  "object_id": <recording_id>,
  "right_type": "master",
  "entity": <label_entity_id>,
  "share": "100.00"
}
```

**Check Checklist**:
- ✅ "Master splits = 100%" should auto-complete

#### Step 4.7: Complete Manual Items
Toggle these manually:
- [ ] Production contracts uploaded
- [ ] Master rights cleared

**Verify Progress**:
- ✅ `checklist_progress` = 100.00

---

### Stage 5: LABEL_RECORDING → MARKETING_ASSETS

**Logged in as**: `label@test.com`

```http
POST /api/songs/<song_id>/send_to_marketing/
```

**Alternative**:
```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "marketing_assets",
  "notes": "Ready for marketing assets"
}
```

**Expected Result**:
- ✅ Song `stage="marketing_assets"`
- ✅ New checklist generated with 5 items (Visual Assets, Promotional Materials, Copy)
- ✅ Alert created for Marketing department
- ✅ `assigned_department` = Marketing

---

### Stage 6: MARKETING_ASSETS (Complete Checklist)

**Logged in as**: `marketing@test.com`

#### Step 6.1: Verify Limited Visibility
```http
GET /api/songs/<song_id>/
```

**Expected**:
- ✅ Can see: title, artist, genre, stage
- ❌ Cannot see: `work`, `work_title`, `internal_notes`, `is_blocked`

#### Step 6.2: Upload Cover Artwork
```http
POST /api/songs/<song_id>/assets/upload/
Content-Type: multipart/form-data

asset_type=cover_art
title=Album Cover
file=<cover_3000x3000.jpg>
```

**Check Checklist**:
- ✅ "Cover artwork uploaded" should auto-complete (if validator implemented)

#### Step 6.3: Upload Press Photo
```http
POST /api/songs/<song_id>/assets/upload/
Content-Type: multipart/form-data

asset_type=press_photo
title=Artist Press Photo
file=<press_photo.jpg>
```

#### Step 6.4: Complete Manual Items
Toggle:
- [ ] Social media assets created
- [ ] Marketing copy written

**Verify Progress**:
- ✅ `checklist_progress` = 100.00

---

### Stage 7: MARKETING_ASSETS → LABEL_REVIEW

**Logged in as**: `marketing@test.com`

```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "label_review",
  "notes": "Assets ready for review"
}
```

**Expected Result**:
- ✅ Song `stage="label_review"`
- ✅ Alert created for Label department ("Assets Submitted")
- ✅ `assigned_department` = Label

---

### Stage 8: LABEL_REVIEW (Review & Approve)

**Logged in as**: `label@test.com`

#### Step 8.1: View Assets
```http
GET /api/songs/<song_id>/assets/
```

#### Step 8.2: Approve Cover Artwork
```http
POST /api/songs/<song_id>/assets/<asset_id>/review/
Content-Type: application/json

{
  "action": "approve",
  "notes": "Looks great!"
}
```

**Expected**:
- ✅ Alert sent to Marketing department ("Assets Approved")

#### Step 8.3: Complete Manual Checklist
Toggle all items in LABEL_REVIEW checklist:
- [ ] Cover artwork approved
- [ ] Press photo approved
- [ ] Promotional materials approved
- [ ] All assets meet technical specs

---

### Stage 9: LABEL_REVIEW → READY_FOR_DIGITAL

**Logged in as**: `label@test.com`

```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "ready_for_digital",
  "notes": "Approved, ready for digital"
}
```

**Expected Result**:
- ✅ Song `stage="ready_for_digital"`
- ✅ New checklist generated (Release Strategy)

---

### Stage 10: READY_FOR_DIGITAL (Prepare for Digital)

**Logged in as**: `label@test.com`

#### Complete Checklist:
- [ ] Release strategy defined
- [ ] Target release date set (already set)
- [ ] Distribution platforms selected

---

### Stage 11: READY_FOR_DIGITAL → DIGITAL_DISTRIBUTION

**Logged in as**: `label@test.com`

```http
POST /api/songs/<song_id>/send_to_digital/
```

**Expected Result**:
- ✅ Song `stage="digital_distribution"`
- ✅ **URGENT** alert created for Digital department
- ✅ `assigned_department` = Digital

---

### Stage 12: DIGITAL_DISTRIBUTION (Create Release)

**Logged in as**: `digital@test.com`

#### Step 12.1: Create Release
```http
POST /api/releases/
Content-Type: application/json

{
  "title": "Test Song Alpha - Single",
  "type": "single",
  "release_date": "2025-12-01"
}
```

#### Step 12.2: Link Release to Song
```python
# Via custom endpoint or Django shell
song.releases.add(release)
```

#### Step 12.3: Add UPC
```http
POST /api/releases/<release_id>/add_upc/
Content-Type: application/json

{
  "upc": "123456789012"
}
```

#### Step 12.4: Add Recording to Release
```http
POST /api/releases/<release_id>/tracks/
Content-Type: application/json

{
  "recording": <recording_id>,
  "position": 1
}
```

#### Step 12.5: Complete Checklist
Toggle all items:
- [ ] Release entity created
- [ ] UPC/EAN assigned
- [ ] Release metadata complete
- [ ] Submitted to distributors
- [ ] Publications created for each platform

---

### Stage 13: DIGITAL_DISTRIBUTION → RELEASED

**Logged in as**: `digital@test.com`

```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "released",
  "notes": "Live on all platforms!"
}
```

**Expected Result**:
- ✅ Song `stage="released"`
- ✅ All departments can view (read-only)
- ✅ No further transitions allowed (except archive)

---

## Permission Testing

### Test 1: Marketing Cannot See Work Details

**Logged in as**: `marketing@test.com`

```http
GET /api/songs/<song_id>/
```

**Verify Response Does NOT Include**:
- ❌ `work`
- ❌ `work_title`
- ❌ `internal_notes`
- ❌ `is_blocked`
- ❌ `blocked_reason`

### Test 2: Sales Can View But Not Edit

**Logged in as**: `sales@test.com`

```http
GET /api/songs/?stage=publishing
```

**Verify**:
- ✅ Can view songs in PUBLISHING stage
- ✅ Can view Work details (read-only)

```http
POST /api/songs/<song_id>/transition/
```

**Verify**:
- ❌ 403 Forbidden (Sales cannot transition)

### Test 3: Digital Cannot See Internal Notes

**Logged in as**: `digital@test.com`

```http
GET /api/songs/<song_id>/
```

**Verify Response Does NOT Include**:
- ❌ `internal_notes`
- ❌ `is_blocked`
- ❌ `blocked_reason`

---

## Validator Testing

### Test Auto-Validators

1. **Work Exists Validator**:
   - Song without work → checklist item incomplete
   - Add work → checklist item auto-completes

2. **ISWC Validator**:
   - Work without ISWC → checklist item incomplete
   - Add ISWC → checklist item auto-completes

3. **Writer Splits Validator**:
   - Splits < 100% → checklist item incomplete
   - Splits = 100% → checklist item auto-completes

4. **Master Audio Validator**:
   - No master audio → checklist item incomplete
   - Upload master → checklist item auto-completes

---

## Alert Testing

### Test Immediate Alerts

1. **Stage Transition Alert**:
   - Transition song to new stage
   - Verify target department receives alert
   - Check `alert_type='stage_transition'`

2. **Send to Digital Alert**:
   - Click "Send to Digital" button
   - Verify Digital dept receives URGENT alert
   - Check `priority='urgent'`

3. **Asset Review Alert**:
   - Marketing submits assets
   - Verify Label receives "Assets Submitted" alert
   - Label approves asset
   - Verify Marketing receives "Assets Approved" alert

### Test Daily Alerts (Requires Celery)

1. **Overdue Alert**:
   - Set `stage_deadline` to yesterday
   - Run: `python manage.py shell -c "from catalog.tasks import run_daily_song_alerts; run_daily_song_alerts()"`
   - Verify assigned user receives overdue alert
   - Verify manager receives overdue alert

2. **Deadline Approaching Alert**:
   - Set `stage_deadline` to 2 days from now
   - Run daily alert task
   - Verify assigned user receives alert

3. **Release Approaching Alert**:
   - Set `target_release_date` to 7 days from now
   - Run daily alert task
   - Verify Digital & Label receive alerts

---

## Checklist Validation Testing

### Test Transition Blocking

**Scenario**: Try to transition with incomplete checklist

```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "label_recording"
}
```

**Expected** (if checklist < 100%):
- ❌ 403 Forbidden
- ❌ Error message: "Checklist must be 100% complete before transitioning (currently 83%)"

### Test Admin Override

**Logged in as**: `admin@test.com`

```http
POST /api/songs/<song_id>/transition/
Content-Type: application/json

{
  "target_stage": "label_recording"
}
```

**Expected**:
- ✅ Transition succeeds even if checklist < 100%
- ✅ Admin bypasses checklist requirement

---

## Troubleshooting

### Issue: Validators Not Auto-Completing

**Check**:
1. Song has relationships set correctly (work, recordings, releases)
2. Run revalidation:
   ```http
   POST /api/songs/<song_id>/checklist/validate/
   ```

### Issue: Alerts Not Created

**Check**:
1. `SongAlert` model exists in database
2. Target department exists with correct code
3. Check logs for exceptions

### Issue: Permission Errors

**Check**:
1. User has `profile` with `department` and `role`
2. Department code matches (lowercase: 'publishing', 'label', 'marketing', 'digital', 'sales')
3. Role level is appropriate (100+ for staff, 1000+ for admin)

---

## Success Criteria

✅ **Full Workflow Complete**:
- Song progresses from DRAFT → RELEASED
- All checklist items validate correctly
- All departments receive appropriate alerts
- Permissions work as expected

✅ **No Errors**:
- No 500 errors
- No validation errors (except expected ones)
- No permission errors (except expected ones)

✅ **Data Integrity**:
- Stage transitions logged in `SongStageTransition`
- Alerts created in `SongAlert`
- Checklist items created for each stage

---

## Next Steps After Testing

1. Fix any bugs discovered during testing
2. Add unit tests for critical validators
3. Add integration tests for workflow transitions
4. Document any edge cases found
5. Train users on the workflow

---

**End of Testing Guide**
