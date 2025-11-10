# Generated migration to update deliverable trigger

from django.db import migrations


def update_deliverable_trigger(apps, schema_editor):
    """Update the Send Deliverable to Marketing trigger to use deliverable entity type."""
    ManualTrigger = apps.get_model('crm_extensions', 'ManualTrigger')
    
    try:
        trigger = ManualTrigger.objects.get(name='Send Deliverable to Marketing')
        # Update entity_type to deliverable instead of opportunity
        trigger.entity_type = 'deliverable'
        trigger.action_config = {
            'task_title_template': 'Create {deliverable.get_deliverable_type_display} for Opportunity "{deliverable.opportunity.name}"',
            'description': 'Create the requested deliverable for this opportunity',
            'target_department': 'marketing',
            'priority': 2,
            'task_type': 'content_creation',
        }
        trigger.save()
    except ManualTrigger.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('crm_extensions', '0010_task_deliverable'),
    ]

    operations = [
        migrations.RunPython(update_deliverable_trigger, migrations.RunPython.noop),
    ]
