#!/usr/bin/env python
"""
Test ISWC auto-validation step by step.
Run this to see EXACTLY what's happening.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, Work, SongChecklistItem
from identity.models import Identifier


def test_iswc_validation():
    """Test ISWC validation step by step"""
    print("\n" + "="*70)
    print("🔍 ISWC AUTO-VALIDATION DIAGNOSTIC")
    print("="*70)

    # Step 1: Find a song in publishing stage
    print("\n📍 STEP 1: Finding songs in 'publishing' stage...")
    songs = Song.objects.filter(stage='publishing')

    if not songs.exists():
        print("❌ No songs found in 'publishing' stage!")
        print("   Create a song in publishing stage first.\n")
        return

    song = songs.first()
    print(f"✅ Found Song #{song.id}: '{song.title}'")

    # Step 2: Check if song has a work
    print(f"\n📍 STEP 2: Checking if song has a work...")
    if not song.work:
        print("❌ Song has NO work linked!")
        print("   Link a work: song.work = work; song.save()")
        return

    work = song.work
    print(f"✅ Song has Work #{work.id}: '{work.title}'")

    # Step 3: Check if work has ISWC
    print(f"\n📍 STEP 3: Checking if work has ISWC...")
    iswc = work.get_iswc()
    if not iswc:
        print("❌ Work has NO ISWC!")
        print("   Create an Identifier:")
        print(f"   Identifier.objects.create(owner_type='work', owner_id={work.id}, scheme='ISWC', value='T-123.456.789-0')")

        # Show if identifier exists but is wrong
        identifiers = Identifier.objects.filter(owner_type='work', owner_id=work.id)
        if identifiers.exists():
            print(f"\n   Found {identifiers.count()} identifier(s):")
            for ident in identifiers:
                print(f"   - {ident.scheme}: {ident.value}")
        return

    print(f"✅ Work has ISWC: {iswc}")

    # Step 4: Check checklist items
    print(f"\n📍 STEP 4: Checking checklist items...")
    all_items = SongChecklistItem.objects.filter(song=song)
    print(f"   Total checklist items: {all_items.count()}")

    if not all_items.exists():
        print("❌ NO checklist items found for this song!")
        print("   Checklist items should be created when song enters 'publishing' stage")
        return

    # Find the ISWC checklist item
    print(f"\n📍 STEP 5: Finding ISWC checklist item...")
    iswc_items = [
        item for item in all_items
        if 'iswc' in item.item_name.lower() or
           (item.validation_rule and item.validation_rule.get('field') == 'iswc')
    ]

    if not iswc_items:
        print("❌ NO ISWC-related checklist item found!")
        print("\n   All checklist items for this song:")
        for item in all_items[:10]:
            print(f"   - {item.item_name} (complete: {item.is_complete})")
            print(f"     validation_type: {item.validation_type}")
            print(f"     validation_rule: {item.validation_rule}")
        return

    iswc_item = iswc_items[0]
    print(f"✅ Found ISWC checklist item: '{iswc_item.item_name}'")
    print(f"   - ID: {iswc_item.id}")
    print(f"   - Complete: {iswc_item.is_complete}")
    print(f"   - Validation Type: {iswc_item.validation_type}")
    print(f"   - Validation Rule: {iswc_item.validation_rule}")

    # Step 6: Test validation logic
    print(f"\n📍 STEP 6: Testing validation logic...")
    print(f"   Calling item.validate()...")

    try:
        is_valid = iswc_item.validate()
        print(f"   Result: {is_valid}")

        if is_valid:
            print("✅ Validation PASSES - ISWC exists!")
            if not iswc_item.is_complete:
                print("⚠️  BUT checklist item is NOT marked complete!")
                print("   This means the signal is NOT firing.")
            else:
                print("✅ Checklist item IS marked complete!")
        else:
            print("❌ Validation FAILS - checking why...")

            # Debug the validation method
            validation_rule = iswc_item.validation_rule or {}
            entity = validation_rule.get('entity')
            field = validation_rule.get('field')

            print(f"\n   Validation rule entity: {entity}")
            print(f"   Validation rule field: {field}")

            if entity == 'work' and song.work:
                print(f"\n   Checking work.get_iswc()...")
                test_iswc = song.work.get_iswc()
                print(f"   work.get_iswc() = {test_iswc}")

                if iswc_item.validation_type == 'auto_field_exists':
                    print(f"\n   Checking getattr(work, '{field}')...")
                    if hasattr(song.work, field):
                        value = getattr(song.work, field, None)
                        print(f"   getattr(work, '{field}') = {value}")
                    else:
                        print(f"   ❌ Work does NOT have attribute '{field}'!")
                        print(f"   This is the problem - validation is checking work.{field}")
                        print(f"   But ISWC is stored in Identifier model, not as work.iswc!")

    except Exception as e:
        print(f"❌ Validation ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Step 7: Test manual update
    print(f"\n📍 STEP 7: Testing manual signal trigger...")
    print(f"   Simulating identifier save...")

    try:
        identifier = Identifier.objects.get(
            owner_type='work',
            owner_id=work.id,
            scheme='ISWC'
        )
        print(f"   Found Identifier #{identifier.id}: {identifier.value}")

        # Check if signal would fire
        print(f"\n   Manually calling validation logic...")
        from identity.signals import _validate_work_checklists

        print(f"   Calling _validate_work_checklists({work.id})...")
        _validate_work_checklists(work.id)

        # Refresh checklist item
        iswc_item.refresh_from_db()
        print(f"\n   After manual trigger:")
        print(f"   - Checklist item complete: {iswc_item.is_complete}")

    except Identifier.DoesNotExist:
        print(f"   ❌ Identifier not found!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("="*70)
    print(f"""
Song: {song.title} (ID: {song.id})
Work: {work.title} (ID: {work.id})
ISWC: {iswc or 'NOT SET'}
Checklist Item: {iswc_item.item_name if iswc_items else 'NOT FOUND'}
Validation Type: {iswc_item.validation_type if iswc_items else 'N/A'}
Validation Rule: {iswc_item.validation_rule if iswc_items else 'N/A'}
Is Complete: {iswc_item.is_complete if iswc_items else 'N/A'}
    """)

    print("="*70 + "\n")


if __name__ == '__main__':
    test_iswc_validation()
