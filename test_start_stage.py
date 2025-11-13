#!/usr/bin/env python
"""
Test the "Start Stage" workflow for marketing stage.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Song, SongChecklistItem, SongStageStatus
from crm_extensions.models import Task
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_start_marketing_stage():
    print("\n" + "="*70)
    print("🎬 START MARKETING STAGE TEST")
    print("="*70)

    # Find a song in marketing_assets stage
    song = Song.objects.filter(stage='marketing_assets').first()

    if not song:
        print("❌ No song found in marketing_assets stage")
        print("   Creating test scenario...")
        # Get any song and set it to marketing
        song = Song.objects.first()
        if song:
            song.stage = 'marketing_assets'
            song.save()
            print(f"✓ Set song #{song.id} to marketing_assets stage")
        else:
            print("❌ No songs found in database")
            return

    print(f"\n📀 Song #{song.id}: '{song.title}'")
    print(f"   Current stage: {song.stage}")

    # Check existing checklist items
    old_checklist_count = SongChecklistItem.objects.filter(
        song=song,
        stage='marketing_assets'
    ).count()
    print(f"\n📋 BEFORE starting stage:")
    print(f"   Marketing checklist items: {old_checklist_count}")

    # Check existing tasks
    old_task_count = Task.objects.filter(
        song=song,
        task_type='content_creation'
    ).count()
    print(f"   Marketing tasks: {old_task_count}")

    # Get marketing manager
    marketing_user = User.objects.filter(email__icontains='marketing').first()
    if marketing_user:
        old_notif_count = Notification.objects.filter(
            user=marketing_user,
            is_read=False
        ).count()
        print(f"\n👤 Marketing manager: {marketing_user.email}")
        print(f"   Unread notifications: {old_notif_count}")

    # Get or create stage status
    stage_status, created = SongStageStatus.objects.get_or_create(
        song=song,
        stage='marketing_assets',
        defaults={'status': 'not_started'}
    )

    if stage_status.status == 'in_progress':
        print(f"\n⚠️  Stage already in progress, resetting to not_started...")
        stage_status.status = 'not_started'
        stage_status.save()

    print(f"\n🔄 Starting marketing stage (changing status to in_progress)...")

    # START THE STAGE
    stage_status.status = 'in_progress'
    stage_status.save()

    print(f"   ✓ Status changed to in_progress")

    # Check results
    print(f"\n📊 AFTER starting stage:")

    # Check checklist items
    new_checklist_count = SongChecklistItem.objects.filter(
        song=song,
        stage='marketing_assets'
    ).count()
    print(f"   Marketing checklist items: {new_checklist_count}")
    print(f"   ➕ New items created: {new_checklist_count - old_checklist_count}")

    if new_checklist_count > old_checklist_count:
        print(f"\n   ✅ Checklist items:")
        for item in SongChecklistItem.objects.filter(song=song, stage='marketing_assets')[:5]:
            print(f"   • {item.description}")
        if new_checklist_count > 5:
            print(f"   ... and {new_checklist_count - 5} more")

    # Check tasks
    new_task_count = Task.objects.filter(
        song=song,
        task_type='content_creation'
    ).count()
    print(f"\n   Marketing tasks: {new_task_count}")
    print(f"   ➕ New tasks created: {new_task_count - old_task_count}")

    # Check notifications
    if marketing_user:
        new_notif_count = Notification.objects.filter(
            user=marketing_user,
            is_read=False
        ).count()
        print(f"\n   Unread notifications: {new_notif_count}")
        print(f"   ➕ New notifications: {new_notif_count - old_notif_count}")

        if new_notif_count > old_notif_count:
            latest = Notification.objects.filter(user=marketing_user).order_by('-created_at').first()
            if latest:
                print(f"\n   Latest notification:")
                print(f"   📬 {latest.message}")

    # Summary
    print(f"\n{'='*70}")
    if new_checklist_count > old_checklist_count:
        print("✅ SUCCESS! Checklist items were created when starting the stage!")
    else:
        print("⚠️  WARNING: No new checklist items were created")

    if new_task_count > old_task_count:
        print("✅ SUCCESS! Marketing task was created!")
    else:
        print("⚠️  WARNING: No new marketing task was created")

    if marketing_user and new_notif_count > old_notif_count:
        print("✅ SUCCESS! Notification was created for marketing manager!")
    else:
        print("⚠️  WARNING: No new notification was created")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_start_marketing_stage()
