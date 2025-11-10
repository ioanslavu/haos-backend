"""
Celery tasks for Song Workflow system.

These tasks run periodically to generate alerts and maintain workflow health.
"""

from celery import shared_task
from catalog.alert_service import create_daily_alerts


@shared_task(name='catalog.run_daily_song_alerts')
def run_daily_song_alerts():
    """
    Daily task to create alerts for overdue songs, approaching deadlines, etc.

    Scheduled to run at midnight every day via Celery Beat.

    Returns:
        Dictionary with summary of alerts created
    """
    summary = create_daily_alerts()

    # Log the results
    print(f"Daily Song Alerts Summary:")
    print(f"  - Overdue alerts: {summary['overdue_alerts']}")
    print(f"  - Deadline approaching alerts: {summary['deadline_approaching_alerts']}")
    print(f"  - Release approaching alerts: {summary['release_approaching_alerts']}")
    print(f"  - Total alerts created: {summary['total_alerts']}")

    return summary
