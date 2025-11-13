#!/usr/bin/env python
"""
Test marketing notification and task creation when song enters marketing stage.
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


def test_marketing_notification():
    """Test that moving song to marketing_assets creates task and notification"""
    print("\n" + "="*70)
    print("🔔 MARKETING NOTIFICATION & TASK CREATION TEST")
    print("="*70)

    # Find a song NOT in marketing stage
    song = Song.objects.exclude(stage='marketing_assets').first()
    if not song:
        print("❌ No suitable song found (need song not in marketing_assets stage)")
        return

    print(f"\n✅ Found Song #{song.id}: '{song.title}'")
    print(f"   Current stage: {song.stage}")

    # Count existing tasks and notifications
    existing_tasks = Task.objects.filter(
        song=song,
        task_type='content_creation',
        title__icontains='marketing'
    )
    print(f"\n   Existing marketing tasks: {existing_tasks.count()}")

    # Get marketing managers
    from api.models import Department
    try:
        marketing_dept = Department.objects.get(code='marketing')
        marketing_managers = User.objects.filter(
            profile__department=marketing_dept,
            profile__role__code__in=['marketing_manager', 'manager']
        )
        print(f"\n   Marketing managers found: {marketing_managers.count()}")
        for manager in marketing_managers:
            print(f"   - {manager.email}")
            existing_notifs = Notification.objects.filter(
                user=manager,
                metadata__song_id=song.id
            ).count()
            print(f"     Existing notifications: {existing_notifs}")
    except Department.DoesNotExist:
        print("   ⚠️  Marketing department not found!")
        return

    # Move song to marketing_assets stage
    print(f"\n🔥 Moving song to 'marketing_assets' stage...")
    old_stage = song.stage
    song.stage = 'marketing_assets'
    song.save()

    print(f"   ✓ Song stage changed from '{old_stage}' to '{song.stage}'")

    # Check if task was created
    new_tasks = Task.objects.filter(
        song=song,
        task_type='content_creation',
        title__icontains='marketing'
    )

    print(f"\n📊 RESULTS:")
    print(f"   Marketing tasks now: {new_tasks.count()}")

    if new_tasks.exists():
        task = new_tasks.first()
        print(f"   ✅ Task created: #{task.id}")
        print(f"      Title: {task.title}")
        print(f"      Status: {task.status}")
        print(f"      Department: {task.department.name if task.department else 'None'}")
        print(f"      Assigned to: {task.assigned_users.count()} user(s)")

        for user in task.assigned_users.all():
            print(f"      - {user.email}")
    else:
        print(f"   ❌ No marketing task created!")

    # Check notifications
    print(f"\n   Notifications:")
    for manager in marketing_managers:
        new_notifs = Notification.objects.filter(
            user=manager,
            metadata__song_id=song.id,
            notification_type='status_change'
        )
        print(f"   - {manager.email}: {new_notifs.count()} notification(s)")

        if new_notifs.exists():
            notif = new_notifs.first()
            print(f"     ✅ Notification #{notif.id}")
            print(f"        Message: {notif.message}")
            print(f"        Read: {notif.is_read}")
            print(f"        Action URL: {notif.action_url}")
        else:
            print(f"     ❌ No notification created!")

    # Summary
    print(f"\n" + "="*70)
    if new_tasks.exists() and all(
        Notification.objects.filter(
            user=manager,
            metadata__song_id=song.id
        ).exists()
        for manager in marketing_managers
    ):
        print("✅ ✅ ✅ SUCCESS! Task and notifications created!")
    else:
        print("❌ ❌ ❌ FAILED! Something didn't work.")
        print("\n🔍 Check Django logs for errors")

    print("="*70 + "\n")


if __name__ == '__main__':
    test_marketing_notification()
