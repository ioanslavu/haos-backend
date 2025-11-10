"""
Celery configuration for async task processing.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('haos')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Periodic task schedule
app.conf.beat_schedule = {
    # Daily task deadline checks (9:00 AM)
    'check-tasks-due-tomorrow': {
        'task': 'notifications.check_tasks_due_tomorrow',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
    },

    # Check for urgent deadlines (every 2 hours, 8 AM - 8 PM)
    'check-tasks-due-soon': {
        'task': 'notifications.check_tasks_due_soon',
        'schedule': crontab(hour='8-20/2', minute=0),  # Every 2 hours from 8 AM to 8 PM
    },

    # Check for inactive tasks (10:00 AM daily)
    'check-inactive-tasks': {
        'task': 'notifications.check_inactive_tasks',
        'schedule': crontab(hour=10, minute=0),  # 10:00 AM daily
    },

    # Check for campaigns ending soon (9:00 AM daily)
    'check-campaigns-ending-soon': {
        'task': 'notifications.check_campaigns_ending_soon',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
    },

    # Check for overdue tasks (every 4 hours, 8 AM - 8 PM)
    'check-overdue-tasks': {
        'task': 'notifications.check_overdue_tasks',
        'schedule': crontab(hour='8-20/4', minute=0),  # Every 4 hours from 8 AM to 8 PM
    },

    # Song workflow daily alerts (midnight)
    'daily-song-alerts': {
        'task': 'catalog.run_daily_song_alerts',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
