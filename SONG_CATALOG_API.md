# Song Catalog Management API

This document describes the API endpoints for managing catalog entities (Works, Recordings, Releases) and featured artists on Songs.

## Base URL

All endpoints are under: `/api/v1/songs/{song_id}/`

## Authentication

All endpoints require authentication via session cookies.

---

## Featured Artists Management

### Add Featured Artist

Add a featured artist to a song with role and display order.

**Endpoint**: `POST /api/v1/songs/{song_id}/add-artist/`

**Request Body**:
```json
{
  "artist_id": 123,
  "role": "featured",  // optional, default: "featured"
  "order": 0           // optional, auto-increments if not provided
}
```

**Role Options**:
- `featured` - Featured Artist (default)
- `remixer` - Remixer
- `producer` - Producer
- `composer` - Composer
- `featuring` - Featuring

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Artist \"Artist Name\" added to song \"Song Title\"",
  "credit_id": 1,
  "artist": {
    "id": 123,
    "name": "Artist Name",
    "role": "featured",
    "order": 0
  }
}
```

**Errors**:
- `400` - Missing artist_id
- `404` - Artist not found

---

### Remove Featured Artist

Remove a featured artist from a song.

**Endpoint**: `DELETE /api/v1/songs/{song_id}/artists/{credit_id}/`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Artist \"Artist Name\" removed from song \"Song Title\""
}
```

**Errors**:
- `404` - Artist credit not found

---

### Reorder Featured Artists

Change the display order of featured artists on a song.

**Endpoint**: `PATCH /api/v1/songs/{song_id}/reorder-artists/`

**Request Body**:
```json
{
  "artist_credits": [
    {"id": 1, "order": 0},
    {"id": 2, "order": 1},
    {"id": 3, "order": 2}
  ]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Artists reordered successfully"
}
```

**Errors**:
- `400` - Missing or invalid artist_credits array
- `404` - Credit ID not found for this song

---

## Recording Management

### Add Recording

Link an existing recording to a song.

**Endpoint**: `POST /api/v1/songs/{song_id}/add-recording/`

**Request Body**:
```json
{
  "recording_id": 456
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Recording \"Recording Title\" added to song \"Song Title\"",
  "recording_id": 456
}
```

**Errors**:
- `400` - Missing recording_id
- `404` - Recording not found

---

### Remove Recording

Unlink a recording from a song.

**Endpoint**: `DELETE /api/v1/songs/{song_id}/recordings/{recording_id}/`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Recording \"Recording Title\" removed from song \"Song Title\""
}
```

**Errors**:
- `404` - Recording not found or not linked to this song

---

## Release Management

### Add Release

Link an existing release to a song.

**Endpoint**: `POST /api/v1/songs/{song_id}/add-release/`

**Request Body**:
```json
{
  "release_id": 789
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Release \"Release Title\" added to song \"Song Title\"",
  "release_id": 789
}
```

**Errors**:
- `400` - Missing release_id
- `404` - Release not found

---

### Remove Release

Unlink a release from a song.

**Endpoint**: `DELETE /api/v1/songs/{song_id}/releases/{release_id}/`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Release \"Release Title\" removed from song \"Song Title\""
}
```

**Errors**:
- `404` - Release not found or not linked to this song

---

## Song Detail Response

When fetching song details via `GET /api/v1/songs/{song_id}/`, the response now includes:

**New Fields**:
```json
{
  "id": 1,
  "title": "Song Title",
  "artist": 123,  // Primary artist ID (FK)

  // New featured artists fields
  "featured_artists": [
    {
      "id": 1,
      "artist_id": 456,
      "artist_name": "Artist Name",
      "artist_display_name": "Artist Display Name",
      "role": "featured",
      "role_display": "Featured Artist",
      "order": 0,
      "created_at": "2025-11-06T10:30:00Z"
    }
  ],

  // All artists combined (primary + featured)
  "all_artists": [
    {
      "id": 123,
      "name": "Primary Artist",
      "role": "primary",
      "is_primary": true,
      "order": -1
    },
    {
      "id": 456,
      "name": "Featured Artist",
      "role": "featured",
      "is_primary": false,
      "order": 0
    }
  ],

  // Formatted display string
  "display_artists": "Primary Artist feat. Featured Artist",

  // Existing fields
  "work": 10,
  "work_title": "Work Title",
  "recordings_count": 2,
  "releases_count": 1
  // ... other fields
}
```

---

## Implementation Details

### SongArtist Model

Through model for M2M relationship between Song and Entity (artist):

**Fields**:
- `song` (FK) - Song this credit belongs to
- `artist` (FK) - Artist entity
- `role` (CharField) - Artist role (featured, remixer, producer, composer, featuring)
- `order` (PositiveIntegerField) - Display order (0 = first)
- `created_at` (DateTime) - When credit was added

**Unique Constraint**: `['song', 'artist', 'role']` - Same artist can have multiple roles on one song

**Ordering**: By `order` field, then `id`

### Helper Methods

**Song.get_all_artists()**:
Returns list of all artists (primary + featured) with metadata:
```python
[
  {
    'id': 123,
    'name': 'Artist Name',
    'role': 'primary',
    'is_primary': True,
    'order': -1
  },
  # ... featured artists
]
```

**Song.add_featured_artist(artist, role='featured', order=None)**:
Convenience method to add featured artist. Auto-increments order if not provided.

**Song.display_artists** (property):
Returns formatted string: "Artist A feat. Artist B, Artist C"

---

## Migration

**Migration File**: `catalog/migrations/0003_add_song_artist_and_featured_artists.py`

**Changes**:
1. Created `SongArtist` model
2. Added `featured_artists` M2M field to `Song` (through SongArtist)
3. Created index on `['song', 'order']` for performance
4. Added unique_together constraint

**Applied**: November 6, 2025

---

## Frontend Integration Notes

### Page-based Navigation Pattern

For creating new catalog entities from song detail page:

1. **Navigate with context**: `/catalog/works/create?songId=123`
2. **Create entity**: User fills form and saves
3. **Link to song**: API call to add-recording/add-release endpoint
4. **Return**: Navigate back to song detail

### Inline Linking Pattern

For linking existing entities:
- Use combobox/search component
- Search existing works/recordings/releases
- Click to link via API
- Immediate UI update

### Artist Management UI

Recommended components:
- **ArtistList**: Display all artists with primary badge
- **ArtistForm**: Add new featured artist with role selector
- **DragHandle**: Reorder artists with drag-and-drop
- **RoleSelect**: Dropdown for role selection

Example reorder flow:
1. User drags artist to new position
2. Calculate new order values
3. POST to `/songs/{id}/reorder-artists/`
4. Update UI optimistically

---

## Testing

### Manual Testing Checklist

- [ ] Add featured artist with default role
- [ ] Add featured artist with custom role and order
- [ ] Remove featured artist
- [ ] Reorder multiple featured artists
- [ ] Add recording to song
- [ ] Remove recording from song
- [ ] Add release to song
- [ ] Remove release from song
- [ ] Verify `display_artists` formats correctly
- [ ] Verify `all_artists` includes primary + featured
- [ ] Test error cases (invalid IDs, missing fields)

### Example Test Commands

```bash
# Add featured artist
curl -X POST http://localhost:8000/api/v1/songs/1/add-artist/ \
  -H "Content-Type: application/json" \
  -d '{"artist_id": 456, "role": "featured"}'

# Reorder artists
curl -X PATCH http://localhost:8000/api/v1/songs/1/reorder-artists/ \
  -H "Content-Type: application/json" \
  -d '{"artist_credits": [{"id": 1, "order": 1}, {"id": 2, "order": 0}]}'

# Add recording
curl -X POST http://localhost:8000/api/v1/songs/1/add-recording/ \
  -H "Content-Type: application/json" \
  -d '{"recording_id": 789}'
```

---

## Related Files

- **Models**: `/backend/catalog/models.py` (lines 1004-1056, 826-833, 1012-1096)
- **Serializers**: `/backend/catalog/serializers.py` (lines 508-519, 560-577)
- **Views**: `/backend/catalog/views.py` (lines 1462-1697)
- **Migration**: `/backend/catalog/migrations/0003_add_song_artist_and_featured_artists.py`
- **Frontend Plan**: `/SONG_CATALOG_PAGES_PLAN.md`
