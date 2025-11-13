#!/usr/bin/env python
"""
Debug script to test checklist auto-validation.
Run this to see what's happening when you save a Work with ISWC.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, Work, SongChecklistItem


def debug_work_checklist():
    """Debug work checklist auto-validation"""
    print("\n" + "="*60)
    print("CHECKLIST AUTO-VALIDATION DEBUG")
    print("="*60)

    # Find all works
    works = Work.objects.all()
    if not works.exists():
        print("\n❌ No works found in database!")
        print("   Create a work first, then run this script.\n")
        return

    print(f"\n📋 Found {works.count()} work(s) in database:")
    for work in works:
        print(f"\n  Work #{work.id}: {work.title}")
        print(f"  ISWC: {work.iswc or '(not set)'}")

        # Find songs linked to this work
        songs = Song.objects.filter(work=work)
        print(f"  Linked songs: {songs.count()}")

        if not songs.exists():
            print("  ⚠️  WARNING: No songs linked to this work!")
            print("     Auto-validation only works when song.work is set!")
            continue

        for song in songs:
            print(f"\n  Song #{song.id}: {song.title}")
            print(f"  Stage: {song.stage}")

            # Find checklist items
            checklist_items = SongChecklistItem.objects.filter(song=song, is_complete=False)
            print(f"  Incomplete checklist items: {checklist_items.count()}")

            if not checklist_items.exists():
                print("  ✅ All checklist items are complete!")
                continue

            # Check work-related items
            work_items = [
                item for item in checklist_items
                if (item.validation_rule or {}).get('entity') == 'work'
            ]

            if not work_items:
                print("  ℹ️  No work-related checklist items found")
                continue

            print(f"\n  Found {len(work_items)} work-related checklist item(s):")
            for item in work_items:
                print(f"\n    📝 {item.item_name}")
                print(f"       Type: {item.validation_type}")
                print(f"       Rule: {item.validation_rule}")
                print(f"       Complete: {item.is_complete}")

                # Test validation
                try:
                    is_valid = item.validate()
                    print(f"       Validation result: {'✅ PASS' if is_valid else '❌ FAIL'}")

                    if is_valid and not item.is_complete:
                        print(f"       🔔 This item SHOULD be auto-completed!")
                        print(f"          Signal should have fired but didn't.")
                    elif not is_valid:
                        # Show why it failed
                        field = item.validation_rule.get('field')
                        if field == 'iswc':
                            print(f"       ℹ️  Reason: work.iswc = '{work.iswc or 'NULL'}'")

                except Exception as e:
                    print(f"       ⚠️  Validation error: {e}")

    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    print("""
1. Make sure the song.work field is set:
   song.work = work
   song.save()

2. Then set the ISWC:
   work.iswc = 'T-123.456.789-0'
   work.save()  # <-- This should trigger auto-validation

3. Check Django logs for signal messages:
   - Look for "Work X: ✓ Auto-completed checklist item..."
   - Look for "Work X: Checking item..."

4. If nothing happens, check that signals are connected:
   - Is catalog/signals.py imported in catalog/apps.py?
   - Check catalog/apps.py -> ready() method

5. Run this script again to see current state
""")
    print("="*60 + "\n")


if __name__ == '__main__':
    debug_work_checklist()
