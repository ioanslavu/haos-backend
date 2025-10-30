"""
Signal handlers for automatic notification generation.

This file will be imported by apps.py when the app is ready.
You can add signal handlers here to automatically create notifications
when certain events occur in your application.

Example usage:

from django.db.models.signals import post_save
from django.dispatch import receiver
from contracts.models import Contract
from .services import NotificationService

@receiver(post_save, sender=Contract)
def notify_contract_assignment(sender, instance, created, **kwargs):
    '''Send notification when a contract is assigned to a user'''
    if instance.assigned_to and not created:
        NotificationService.notify_assignment(
            user=instance.assigned_to,
            assigned_by=instance.created_by,
            object_name=f"Contract #{instance.contract_number}",
            object_type="contract",
            action_url=f"/contracts/{instance.id}"
        )
"""

# Import your models and add signal handlers below
# from django.db.models.signals import post_save, pre_save
# from django.dispatch import receiver
# from .services import NotificationService


# Example: Uncomment and customize when you need assignment notifications
# @receiver(post_save, sender=YourModel)
# def notify_on_assignment(sender, instance, created, **kwargs):
#     if instance.assigned_to:
#         NotificationService.notify_assignment(
#             user=instance.assigned_to,
#             assigned_by=instance.assigned_by or instance.created_by,
#             object_name=str(instance),
#             object_type=sender.__name__.lower(),
#             action_url=f"/{sender.__name__.lower()}s/{instance.id}"
#         )
