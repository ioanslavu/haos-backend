#!/usr/bin/env python
"""
Test writer auto-validation.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, Work, SongChecklistItem
from rights.models import Split
from identity.models import Entity


def test_writer_validation():
    """Test that adding a writer auto-completes checklist"""
    print("\n" + "="*70)
    print("🔍 WRITER AUTO-VALIDATION TEST")
    print("="*70)

    # Find a song in publishing stage
    song = Song.objects.filter(stage='publishing').first()
    if not song or not song.work:
        print("❌ No suitable song found (need song in 'publishing' stage with work)")
        return

    work = song.work
    print(f"\n✅ Found Song #{song.id}: '{song.title}'")
    print(f"✅ Work #{work.id}: '{work.title}'")

    # Find writer checklist item
    writer_item = SongChecklistItem.objects.filter(
        song=song,
        validation_rule__entity='work_writers'
    ).first()

    if not writer_item:
        print("❌ No writer checklist item found")
        return

    print(f"\n📝 Writer Checklist Item: '{writer_item.item_name}'")
    print(f"   Validation Type: {writer_item.validation_type}")
    print(f"   Validation Rule: {writer_item.validation_rule}")
    print(f"   Complete BEFORE: {writer_item.is_complete}")

    # Count current writers
    current_writers = Split.objects.filter(
        scope='work',
        object_id=work.id,
        right_type='writer'
    )
    print(f"\n   Current writers: {current_writers.count()}")
    for split in current_writers:
        print(f"   - {split.entity.display_name}: {split.share}%")

    # If no writers, add one
    if not current_writers.exists():
        # Find or create a writer entity
        writer_entity = Entity.objects.filter(kind='PF').first()
        if not writer_entity:
            writer_entity = Entity.objects.create(
                display_name='Test Writer',
                kind='PF'
            )

        print(f"\n🔥 Creating writer split for {writer_entity.display_name}...")
        split = Split.objects.create(
            scope='work',
            object_id=work.id,
            entity=writer_entity,
            right_type='writer',
            share=100.00
        )
        print(f"   ✓ Created Split #{split.id}")

        # Refresh checklist item
        writer_item.refresh_from_db()

        print(f"\n📊 RESULT:")
        print(f"   Writers count: {Split.objects.filter(scope='work', object_id=work.id, right_type='writer').count()}")
        print(f"   Checklist Complete AFTER: {writer_item.is_complete}")

        if writer_item.is_complete:
            print(f"\n✅ ✅ ✅ SUCCESS! Writer added and checklist auto-completed!")
        else:
            print(f"\n❌ ❌ ❌ FAILED! Checklist item is still not complete.")

            # Debug validation
            print(f"\n🔍 Debug:")
            print(f"   Testing validation manually...")
            is_valid = writer_item.validate()
            print(f"   item.validate() returns: {is_valid}")
    else:
        print(f"\n⚠️  Work already has {current_writers.count()} writer(s)")
        print(f"   Checklist complete: {writer_item.is_complete}")

        if not writer_item.is_complete:
            print(f"\n   🔧 Marking as incomplete and triggering validation...")
            writer_item.is_complete = False
            writer_item.save()

            # Trigger validation by re-saving a split
            split = current_writers.first()
            split.share = split.share  # No change, just trigger signal
            split.save()

            writer_item.refresh_from_db()
            print(f"   Checklist complete after trigger: {writer_item.is_complete}")

    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    test_writer_validation()
