#!/usr/bin/env python
"""
Test that marketing checklist is created when song enters marketing stage.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, SongChecklistItem
from catalog import checklist_templates

def test_marketing_checklist():
    print("\n" + "="*70)
    print("🎨 MARKETING CHECKLIST TEST")
    print("="*70)

    # Check template
    template = checklist_templates.MARKETING_ASSETS_CHECKLIST_TEMPLATE
    print(f"\n✅ Marketing template has {len(template)} items")
    for i, item in enumerate(template[:5], 1):
        print(f"   {i}. [{item['category']}] {item['item_name']}")
    if len(template) > 5:
        print(f"   ... and {len(template) - 5} more")

    # Find a song in marketing_assets stage
    marketing_song = Song.objects.filter(stage='marketing_assets').first()

    if marketing_song:
        print(f"\n📀 Found Song #{marketing_song.id}: '{marketing_song.title}'")
        print(f"   Stage: {marketing_song.stage}")

        # Count checklist items
        checklist_items = SongChecklistItem.objects.filter(
            song=marketing_song,
            stage='marketing_assets'
        )
        print(f"   Checklist items: {checklist_items.count()}")

        if checklist_items.exists():
            print("\n   📋 Checklist items:")
            for item in checklist_items[:10]:
                status = "✓" if item.is_complete else "○"
                print(f"      {status} [{item.category}] {item.item_name}")
        else:
            print("\n   ❌ NO CHECKLIST ITEMS FOUND!")
            print("   This means items weren't created when song entered marketing stage")
    else:
        print("\n   ℹ️  No song currently in marketing_assets stage")
        print("   Try transitioning a song to marketing_assets and run this again")

    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    test_marketing_checklist()
