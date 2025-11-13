#!/usr/bin/env python
"""
Manually create marketing checklist for songs in marketing_assets stage.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, SongChecklistItem
from catalog import checklist_templates

def fix_marketing_checklist():
    print("\n" + "="*70)
    print("🔧 FIXING MARKETING CHECKLIST")
    print("="*70)

    # Find all songs in marketing_assets stage
    marketing_songs = Song.objects.filter(stage='marketing_assets')
    print(f"\n📀 Found {marketing_songs.count()} song(s) in marketing_assets stage")

    for song in marketing_songs:
        # Check if checklist already exists
        existing_items = SongChecklistItem.objects.filter(
            song=song,
            stage='marketing_assets'
        ).count()

        print(f"\n   Song #{song.id}: '{song.title}'")
        print(f"   Existing checklist items: {existing_items}")

        if existing_items == 0:
            print(f"   ⚠️  Creating checklist items...")

            # Generate checklist items
            checklist_items_data = checklist_templates.generate_checklist_for_stage(song, 'marketing_assets')

            created_count = 0
            for item_data in checklist_items_data:
                SongChecklistItem.objects.create(**item_data)
                created_count += 1

            print(f"   ✅ Created {created_count} checklist items")
        else:
            print(f"   ✓ Checklist already exists")

    print("\n" + "="*70)
    print("✅ Done!")
    print("="*70 + "\n")


if __name__ == '__main__':
    fix_marketing_checklist()
