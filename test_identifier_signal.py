#!/usr/bin/env python
"""
Test that Identifier signal actually fires when saving.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, Work, SongChecklistItem
from identity.models import Identifier


def test_identifier_signal():
    """Test that saving an Identifier triggers checklist validation"""
    print("\n" + "="*70)
    print("🔥 TESTING IDENTIFIER SIGNAL AUTO-FIRE")
    print("="*70)

    # Find a song in publishing stage
    song = Song.objects.filter(stage='publishing').first()
    if not song or not song.work:
        print("❌ No suitable song found (need song in 'publishing' stage with work)")
        return

    work = song.work
    print(f"\n✅ Found Song #{song.id}: '{song.title}'")
    print(f"✅ Work #{work.id}: '{work.title}'")

    # Find ISWC checklist item
    iswc_item = SongChecklistItem.objects.filter(
        song=song,
        validation_rule__field='iswc'
    ).first()

    if not iswc_item:
        print("❌ No ISWC checklist item found")
        return

    print(f"\n📝 ISWC Checklist Item: '{iswc_item.item_name}'")
    print(f"   Complete BEFORE: {iswc_item.is_complete}")

    # Get or create identifier
    identifier, created = Identifier.objects.get_or_create(
        owner_type='work',
        owner_id=work.id,
        scheme='ISWC',
        defaults={'value': 'T-000.000.000-0'}
    )

    print(f"\n{'📝 Created' if created else '✏️  Updated'} Identifier #{identifier.id}")
    print(f"   Scheme: {identifier.scheme}")
    print(f"   Value BEFORE: {identifier.value}")

    # Change the value and save (this should trigger signal!)
    new_value = 'T-999.888.777-6'
    identifier.value = new_value
    print(f"\n🔥 Saving identifier with new value: {new_value}")
    print(f"   This should trigger identity.signals.on_identifier_saved()")
    identifier.save()

    # Refresh checklist item from database
    iswc_item.refresh_from_db()

    print(f"\n📊 RESULT:")
    print(f"   Identifier Value AFTER: {identifier.value}")
    print(f"   Checklist Complete AFTER: {iswc_item.is_complete}")

    if iswc_item.is_complete:
        print(f"\n✅ ✅ ✅ SUCCESS! Signal fired and checklist auto-completed!")
    else:
        print(f"\n❌ ❌ ❌ FAILED! Checklist item is still not complete.")
        print(f"\n🔍 Debugging:")
        print(f"   - Check Django logs for 'Identifier ISWC:' messages")
        print(f"   - Verify identity/signals.py is imported in identity/apps.py")
        print(f"   - Restart Django server to reload signal handlers")

    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    test_identifier_signal()
