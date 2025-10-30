#!/usr/bin/env python
"""
Test script for notification system

Usage:
    python test_notifications.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.services import NotificationService

User = get_user_model()

def test_create_notification():
    """Create a test notification"""
    # Get first user
    user = User.objects.first()

    if not user:
        print("L No users found in database. Please create a user first.")
        return

    print(f" Found user: {user.email}")

    # Create notification
    notification = NotificationService.create_notification(
        user=user,
        message="<‰ Test notification - Your notification system is working!",
        notification_type="system",
        action_url="/dashboard",
        metadata={
            "test": True,
            "created_by": "test_script"
        }
    )

    print(f" Created notification ID: {notification.id}")
    print(f"   Message: {notification.message}")
    print(f"   Type: {notification.notification_type}")
    print(f"   User: {notification.user.email}")
    print(f"   Created: {notification.created_at}")

    print("\n<¯ Notification created successfully!")
    print("   - Check your frontend to see the notification appear in real-time")
    print("   - It should show as a toast and appear in the bell dropdown")

def test_assignment_notification():
    """Create a test assignment notification"""
    users = User.objects.all()[:2]

    if len(users) < 2:
        print("   Need at least 2 users to test assignment notifications")
        return

    assigned_to = users[0]
    assigned_by = users[1]

    notification = NotificationService.notify_assignment(
        user=assigned_to,
        assigned_by=assigned_by,
        object_name="Contract #12345",
        object_type="contract",
        action_url="/contracts/12345"
    )

    print(f"\n Created assignment notification ID: {notification.id}")
    print(f"   {assigned_by.email} assigned {assigned_to.email} to Contract #12345")

if __name__ == "__main__":
    print("=" * 60)
    print("= Notification System Test")
    print("=" * 60)
    print()

    try:
        test_create_notification()
        print()
        test_assignment_notification()

        print("\n" + "=" * 60)
        print("( All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nL Error: {e}")
        import traceback
        traceback.print_exc()
