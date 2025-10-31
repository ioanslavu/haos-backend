# Bulk Entity Import Guide

This guide explains how to import large numbers of entities into your HaOS instance, with support for profile photos from S3, local files, or HTTP URLs.

## Overview

The entity import system supports:
- ✅ **JSON fixture files** - Structured entity data
- ✅ **Profile photos from S3 URLs** - Photos already in cloud storage
- ✅ **Profile photos from HTTP URLs** - Downloads automatically
- ✅ **Profile photos from local files** - For offline imports
- ✅ **Social media accounts** - Automatic linking
- ✅ **Entity roles** - Including is_internal flag
- ✅ **Dry-run mode** - Preview before importing
- ✅ **Update existing** - Update entities that already exist

## Quick Start

### 1. Export From Production (One-Time Setup)

On your production server with the 32 internal artists:

```bash
# Export internal artists with S3 URLs
python manage.py export_artists_fixture --internal-only --output artists_fixture.json
```

This creates `artists_fixture.json` with:
- All 32 HaHaHa Production artists
- S3 photo URLs (no need to copy files!)
- Social media accounts
- Entity roles with is_internal=true

### 2. Import On Any Server

On staging, local dev, or a new production server:

```bash
# Dry run first (preview what will be imported)
python manage.py import_entities_fixture artists_fixture.json --dry-run

# Actually import
python manage.py import_entities_fixture artists_fixture.json
```

Photos will be **automatically downloaded from S3** and stored in your local media folder (or re-uploaded to S3 if USE_S3=True).

## Command Reference

### Export Command

```bash
python manage.py export_artists_fixture [OPTIONS]
```

**Options:**
- `--output FILE` - Output file path (default: `artists_fixture.json`)
- `--internal-only` - Export only internal artists (is_internal=True)

**Examples:**

```bash
# Export all entities
python manage.py export_artists_fixture --output all_entities.json

# Export only internal artists
python manage.py export_artists_fixture --internal-only --output internal_artists.json
```

### Import Command

```bash
python manage.py import_entities_fixture FIXTURE_FILE [OPTIONS]
```

**Options:**
- `--dry-run` - Preview import without saving to database
- `--skip-photos` - Skip downloading/importing profile photos
- `--update-existing` - Update existing entities instead of skipping them

**Examples:**

```bash
# Preview what will be imported
python manage.py import_entities_fixture artists.json --dry-run

# Import (skip photos if already uploaded separately)
python manage.py import_entities_fixture artists.json --skip-photos

# Update existing entities (re-import with new data)
python manage.py import_entities_fixture artists.json --update-existing
```

## JSON Fixture Format

The fixture file is a JSON array of entity objects:

```json
[
  {
    "kind": "PF",
    "display_name": "Smiley",
    "first_name": "Andrei",
    "last_name": "Tiberiu Maria",
    "stage_name": "Smiley",
    "nationality": "Romanian",
    "gender": null,
    "email": "smiley@example.com",
    "phone": "+40123456789",
    "address": "",
    "city": "Bucharest",
    "state": "",
    "zip_code": "",
    "country": "Romania",
    "notes": "Leading Romanian artist",
    "profile_photo_url": "https://bucket.s3.amazonaws.com/media/entity_photos/smiley.jpg",
    "roles": [
      {
        "role": "artist",
        "primary_role": true,
        "is_internal": true
      }
    ],
    "social_media": [
      {
        "platform": "instagram",
        "handle": "smiley_omul",
        "url": "https://www.instagram.com/smiley_omul/",
        "display_name": "Smiley",
        "follower_count": 2500000,
        "is_verified": true,
        "is_primary": true,
        "notes": ""
      },
      {
        "platform": "spotify",
        "handle": "",
        "url": "https://open.spotify.com/artist/3gvNMbcnvmnjGaG6hvJfSH",
        "display_name": "Smiley",
        "follower_count": null,
        "is_verified": false,
        "is_primary": false,
        "notes": ""
      }
    ]
  }
]
```

### Required Fields

- `kind` - "PF" (Physical Person) or "PJ" (Legal Entity)
- `display_name` - Main entity name

### Optional Fields

All other fields are optional and will default to empty string or null.

### Photo URL Types

The `profile_photo_url` field supports:

1. **S3 URLs** (recommended):
   ```
   "https://bucket.s3.region.amazonaws.com/media/entity_photos/photo.jpg"
   ```

2. **Any HTTP/HTTPS URL**:
   ```
   "https://example.com/photos/artist.jpg"
   ```

3. **Local file paths** (if photos are in same directory as fixture):
   ```
   "photos/artist.jpg"  # Relative to fixture file location
   ```

## Common Workflows

### Workflow 1: Deploy to New Server

You've set up a new production server and want to import all artists:

```bash
# On old/staging server - export artists
python manage.py export_artists_fixture --internal-only --output artists.json

# Copy file to new server
scp artists.json user@new-server:/path/to/backend/

# On new server - import
python manage.py import_entities_fixture artists.json
```

Result: All 32 artists imported with photos downloaded from S3.

### Workflow 2: Add Bulk External Entities

You have a list of 100 external entities (labels, publishers, etc.) in CSV:

1. Convert CSV to JSON fixture format (write a Python script)
2. Optional: Add profile photos to S3 first
3. Import:
   ```bash
   python manage.py import_entities_fixture external_entities.json
   ```

### Workflow 3: Update Existing Data

Artists' social media changed, need to update:

```bash
# Export current data
python manage.py export_artists_fixture --output current.json

# Edit current.json (update social media URLs, follower counts, etc.)

# Re-import with updates
python manage.py import_entities_fixture current.json --update-existing
```

### Workflow 4: Migrate from Local to S3

Currently using local photos, want to move to S3:

```bash
# Step 1: Upload local photos to S3
python manage.py upload_media_to_s3

# Step 2: Export with S3 URLs
python manage.py export_artists_fixture --output artists_s3.json

# Step 3: Store this file for future deployments
git add artists_s3.json
git commit -m "Add artists fixture with S3 URLs"
```

Now any new server can import from this fixture.

## Creating Custom Fixture Files

### From Spreadsheet/CSV

```python
import csv
import json

entities = []

with open('entities.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        entity = {
            "kind": "PF",  # or "PJ" for companies
            "display_name": row['name'],
            "first_name": row.get('first_name', ''),
            "last_name": row.get('last_name', ''),
            "email": row.get('email', ''),
            "phone": row.get('phone', ''),
            "profile_photo_url": row.get('photo_url', ''),
            "roles": [
                {
                    "role": row.get('role', 'artist'),
                    "primary_role": True,
                    "is_internal": row.get('is_internal', 'false').lower() == 'true'
                }
            ],
            "social_media": []
        }
        entities.append(entity)

with open('entities_fixture.json', 'w') as f:
    json.dump(entities, f, indent=2)
```

Then import:
```bash
python manage.py import_entities_fixture entities_fixture.json
```

### From API/Scraping

```python
import requests
import json

# Example: Fetch artists from external API
response = requests.get('https://api.example.com/artists')
api_artists = response.json()

entities = []
for artist in api_artists:
    entity = {
        "kind": "PF",
        "display_name": artist['name'],
        "stage_name": artist.get('stage_name', ''),
        "profile_photo_url": artist.get('image_url', ''),
        "roles": [{"role": "artist", "primary_role": True, "is_internal": False}],
        "social_media": [
            {
                "platform": "instagram",
                "url": artist.get('instagram_url', ''),
                "handle": artist.get('instagram_handle', ''),
                "is_primary": True,
                "is_verified": False,
                "follower_count": None,
                "display_name": "",
                "notes": ""
            }
        ] if artist.get('instagram_url') else []
    }
    entities.append(entity)

with open('api_artists.json', 'w') as f:
    json.dump(entities, f, indent=2)
```

## Performance Tips

**Large Imports (100+ entities):**
- Photos download sequentially, may take time
- Use `--skip-photos` to import data first, then:
  ```bash
  # Upload photos separately to S3 first
  python upload_photos_to_s3.py

  # Then import without photo download
  python manage.py import_entities_fixture huge_list.json --skip-photos
  ```

**Update Existing:**
- With `--update-existing`, the import deletes and recreates roles/social media
- Use for full data refresh, not just adding new fields

## Troubleshooting

### Photos not downloading

**Issue**: `profile_photo_url` in fixture but photos aren't importing

**Check**:
1. URL is accessible: `curl -I <photo_url>`
2. No firewall blocking download
3. URL returns image content type
4. Try `--skip-photos` flag if intentional

### Duplicate entities

**Issue**: "Already exists (skipping)" for entities you want to import

**Solution**: Use `--update-existing` flag to update instead of skip

### S3 photos not accessible

**Issue**: Imported but photos show 403 Forbidden

**Fix**:
1. Check S3 bucket policy allows public read
2. Ensure bucket ACL settings allow public access
3. Verify IAM user has s3:PutObject permission

## Best Practices

1. **Always dry-run first**: `--dry-run` to preview changes
2. **Version control fixtures**: Commit fixture files to git
3. **Use S3 for production**: Set `USE_S3=True` in production .env
4. **Separate internal/external**: Export internal artists separately
5. **Regular exports**: Export weekly as backup

## Support

For issues with:
- **Import/Export commands**: Check `backend/identity/management/commands/`
- **JSON format**: See fixture examples above
- **S3 integration**: See `backend/AWS_S3_SETUP.md`
