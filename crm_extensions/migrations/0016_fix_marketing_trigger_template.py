# Generated migration to fix marketing deliverable trigger template

from django.db import migrations


def fix_marketing_trigger_template(apps, schema_editor):
    """
    Fix the template in existing marketing trigger - change {opportunity.name} to {opportunity.title}
    """
    ManualTrigger = apps.get_model('crm_extensions', 'ManualTrigger')

    try:
        trigger = ManualTrigger.objects.get(name='Send Deliverable to Marketing')

        # Update the action_config with correct field name
        if trigger.action_config:
            config = trigger.action_config

            # Fix task_title_template
            if 'task_title_template' in config:
                config['task_title_template'] = config['task_title_template'].replace(
                    '{opportunity.name}',
                    '{opportunity.title}'
                )

            # Fix task_description_template
            if 'task_description_template' in config:
                config['task_description_template'] = config['task_description_template'].replace(
                    '{opportunity.name}',
                    '{opportunity.title}'
                )

            trigger.action_config = config
            trigger.save()
            print(f"✓ Updated trigger template: {config.get('task_title_template')}")

    except ManualTrigger.DoesNotExist:
        print("⚠ Marketing trigger not found, skipping")


def reverse_fix(apps, schema_editor):
    """Reverse the fix (optional)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('crm_extensions', '0015_update_marketing_deliverable_trigger'),
    ]

    operations = [
        migrations.RunPython(fix_marketing_trigger_template, reverse_fix),
    ]
