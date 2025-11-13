#!/usr/bin/env python
"""
Test moving a fresh song to marketing to see if notifications are created.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song
from crm_extensions.models import Task
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_fresh_marketing():
    print("\n" + "="*70)
    print("🎬 FRESH MARKETING TRANSITION TEST")
    print("="*70)

    # Find a song NOT in marketing stage
    song = Song.objects.exclude(stage='marketing_assets').first()

    if not song:
        print("❌ No suitable song found (need song not in marketing_assets)")
        return

    print(f"\n📀 Song #{song.id}: '{song.title}'")
    print(f"   Current stage: {song.stage}")

    # Count existing notifications for marketing manager
    marketing_user = User.objects.filter(email__icontains='marketing').first()
    if marketing_user:
        old_notif_count = Notification.objects.filter(
            user=marketing_user,
            is_read=False
        ).count()
        print(f"\n👤 Marketing user: {marketing_user.email}")
        print(f"   Unread notifications before: {old_notif_count}")

    # Transition to marketing
    print(f"\n🔄 Moving song to marketing_assets stage...")
    old_stage = song.stage
    song.stage = 'marketing_assets'
    song.save()

    print(f"   ✓ Stage changed from '{old_stage}' to '{song.stage}'")

    # Check new notifications
    if marketing_user:
        new_notif_count = Notification.objects.filter(
            user=marketing_user,
            is_read=False
        ).count()
        print(f"\n📊 RESULTS:")
        print(f"   Unread notifications after: {new_notif_count}")
        print(f"   New notifications created: {new_notif_count - old_notif_count}")

        # Show latest notifications
        latest_notifs = Notification.objects.filter(
            user=marketing_user
        ).order_by('-created_at')[:3]

        print(f"\n   Latest notifications for {marketing_user.email}:")
        for notif in latest_notifs:
            status = "✓" if notif.is_read else "○"
            print(f"   {status} #{notif.id} [{notif.notification_type}] {notif.message[:60]}...")
            print(f"      Created: {notif.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check task
    task = Task.objects.filter(song=song, task_type='content_creation').first()
    if task:
        print(f"\n   ✅ Task created: #{task.id}")
        print(f"      Title: {task.title}")
        print(f"      Assigned to: {task.assigned_users.count()} user(s)")

    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    test_fresh_marketing()
