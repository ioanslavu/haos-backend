#!/usr/bin/env python
"""
Test the "Send to Marketing" workflow to verify checklist creation.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, SongChecklistItem
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from catalog.views import SongViewSet

User = get_user_model()

def test_send_to_marketing():
    print("\n" + "="*70)
    print("🎬 SEND TO MARKETING WORKFLOW TEST")
    print("="*70)

    # Find a song in label_recording stage
    song = Song.objects.filter(stage='label_recording').first()

    if not song:
        print("❌ No song found in label_recording stage")
        # Try to create/transition one
        song = Song.objects.exclude(stage='marketing_assets').first()
        if song:
            print(f"📀 Using Song #{song.id}: '{song.title}' (stage: {song.stage})")
            print(f"   ⚠️  Manually setting to label_recording for test...")
            song.stage = 'label_recording'
            song.save()
        else:
            print("❌ No suitable song found")
            return

    print(f"\n📀 Song #{song.id}: '{song.title}'")
    print(f"   Current stage: {song.stage}")

    # Check existing checklist items
    old_items = SongChecklistItem.objects.filter(song=song)
    marketing_items_before = old_items.filter(stage='marketing_assets').count()
    print(f"\n📋 Checklist items BEFORE send_to_marketing:")
    print(f"   Total items: {old_items.count()}")
    print(f"   Marketing items: {marketing_items_before}")

    # Get a user to make the request
    user = User.objects.filter(is_staff=True).first()
    if not user:
        user = User.objects.first()

    print(f"\n👤 Request user: {user.email}")

    # Simulate API request
    factory = APIRequestFactory()
    request = factory.post(f'/api/v1/songs/{song.id}/send_to_marketing/')
    request.user = user

    # Call the send_to_marketing endpoint
    viewset = SongViewSet()
    viewset.format_kwarg = None

    print(f"\n🔄 Calling send_to_marketing endpoint...")

    try:
        response = viewset.send_to_marketing(request, pk=song.id)

        if response.status_code == 200:
            print(f"   ✅ Success! Status: {response.status_code}")

            # Refresh song
            song.refresh_from_db()
            print(f"\n📊 AFTER send_to_marketing:")
            print(f"   New stage: {song.stage}")

            # Check checklist items
            new_items = SongChecklistItem.objects.filter(song=song)
            marketing_items_after = new_items.filter(stage='marketing_assets').count()

            print(f"\n📋 Checklist items AFTER:")
            print(f"   Total items: {new_items.count()}")
            print(f"   Marketing items: {marketing_items_after}")
            print(f"   ➕ New marketing items created: {marketing_items_after - marketing_items_before}")

            if marketing_items_after > 0:
                print(f"\n   Marketing checklist items:")
                for item in new_items.filter(stage='marketing_assets'):
                    print(f"   • {item.description}")

            if marketing_items_after - marketing_items_before > 0:
                print(f"\n✅ SUCCESS! Checklist items were created!")
            else:
                print(f"\n⚠️  WARNING: No new checklist items were created")

        else:
            print(f"   ❌ Failed! Status: {response.status_code}")
            print(f"   Error: {response.data}")

    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    test_send_to_marketing()
