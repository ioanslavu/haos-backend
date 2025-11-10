"""
Contract signals for Universal Task Automation System.

Automatically advances tasks and checks stage advancement when contracts change.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Contract

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Contract)
def track_contract_field_changes(sender, instance, **kwargs):
    """
    Track old field values before save for change detection.

    Stores old status in _old_status attribute for comparison in post_save.
    """
    if instance.pk:  # Existing contract
        try:
            old_contract = Contract.objects.get(pk=instance.pk)
            instance._old_status = old_contract.status
        except Contract.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Contract)
def on_contract_saved(sender, instance, created, **kwargs):
    """
    Handle contract save events.

    Actions:
    1. Update contract task titles when status changes

    Args:
        sender: Contract model class
        instance: Contract instance that was saved
        created: True if this is a new contract
        **kwargs: Additional signal arguments
    """
    try:
        # Update contract task titles when status changes
        if hasattr(instance, '_old_status') and instance._old_status != instance.status:
            _update_contract_task_titles(instance)

    except Exception as e:
        logger.error(f"Error in contract post_save signal for Contract {instance.id}: {e}")


def _update_contract_task_titles(contract):
    """
    Update task titles for contract watching tasks when contract status changes.

    Task title format:
    - Draft: "Contract for Work 'X': Draft"
    - Pending Signature: "Contract for Work 'X': Pending Signature"
    - Signed: "Contract for Work 'X': Signed"
    - etc.

    Args:
        contract: Contract instance
    """
    from crm_extensions.models import Task

    try:
        # Find all tasks linked to this contract
        # Check both work and recording (contracts can be for either)
        tasks_to_update = []

        # Find tasks via ContractScope relationships
        for scope in contract.scopes.all():
            if scope.work:
                # Find tasks for this work
                work_tasks = Task.objects.filter(
                    work=scope.work,
                    task_type='contract_prep'
                )
                tasks_to_update.extend(work_tasks)

            elif scope.recording:
                # Find tasks for this recording
                recording_tasks = Task.objects.filter(
                    recording=scope.recording,
                    task_type='contract_prep'
                )
                tasks_to_update.extend(recording_tasks)

        # Update task titles based on contract status
        status_display = contract.get_status_display()

        for task in tasks_to_update:
            # Determine entity name
            if task.work:
                entity_name = task.work.title
                entity_type = "Work"
            elif task.recording:
                entity_name = task.recording.title
                entity_type = "Recording"
            else:
                continue

            # Update task title
            new_title = f"Contract for {entity_type} '{entity_name}': {status_display}"
            if task.title != new_title:
                task.title = new_title
                task.save(update_fields=['title'])
                logger.info(
                    f"Updated task {task.id} title to reflect contract status: {status_display}"
                )

    except Exception as e:
        logger.error(f"Error updating contract task titles for Contract {contract.id}: {e}")
