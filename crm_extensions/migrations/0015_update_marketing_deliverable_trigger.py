# Generated migration to update marketing deliverable trigger

from django.db import migrations


def update_marketing_deliverable_trigger(apps, schema_editor):
    """
    Update the 'Send Deliverable to Marketing' trigger with proper configuration.
    - Task title: Marketing request: [deliverable_type] for [opportunity_name]
    - Description includes: deliverable type, quantity, due date, and links
    - Visible to managers in relevant departments
    """
    ManualTrigger = apps.get_model('crm_extensions', 'ManualTrigger')
    Department = apps.get_model('api', 'Department')

    try:
        trigger = ManualTrigger.objects.get(name='Send Deliverable to Marketing')

        # Update configuration with user specifications
        trigger.entity_type = 'deliverable'
        trigger.context = 'opportunity_detail'
        trigger.button_label = 'Send to Marketing'
        trigger.button_style = 'primary'
        trigger.action_type = 'create_task'
        trigger.action_config = {
            'task_title_template': 'Marketing request: {deliverable_type} for {opportunity.title}',
            'task_description_template': (
                'Deliverable Request Details:\n\n'
                'Type: {deliverable_type}\n'
                'Quantity: {quantity}\n'
                'Due Date: {due_date}\n'
                'Status: {status}\n\n'
                'Description:\n{description}\n\n'
                'Links:\n'
                '- Deliverable: /opportunities/{opportunity.id}?tab=deliverables\n'
                '- Opportunity: /opportunities/{opportunity.id}'
            ),
            'target_department': 'Marketing Department',
            'priority': 2,
            'task_type': 'content_creation',
        }
        trigger.required_permissions = []  # No button restrictions - task RBAC handled separately
        trigger.is_active = True
        trigger.save()

        # Set department visibility - only Sales department can see the button
        try:
            sales_dept = Department.objects.get(name='Sales Department')

            # Clear existing and set new departments
            trigger.visible_to_departments.clear()
            trigger.visible_to_departments.add(sales_dept)  # Only Sales, not Marketing!
        except Department.DoesNotExist:
            # Departments don't exist yet, skip visibility setup
            pass

    except ManualTrigger.DoesNotExist:
        # Trigger doesn't exist, create it
        trigger = ManualTrigger.objects.create(
            name='Send Deliverable to Marketing',
            button_label='Send to Marketing',
            button_style='primary',
            entity_type='deliverable',
            context='opportunity_detail',
            action_type='create_task',
            action_config={
                'task_title_template': 'Marketing request: {deliverable_type} for {opportunity.title}',
                'task_description_template': (
                    'Deliverable Request Details:\n\n'
                    'Type: {deliverable_type}\n'
                    'Quantity: {quantity}\n'
                    'Due Date: {due_date}\n'
                    'Status: {status}\n\n'
                    'Description:\n{description}\n\n'
                    'Links:\n'
                    '- Deliverable: /opportunities/{opportunity.id}?tab=deliverables\n'
                    '- Opportunity: /opportunities/{opportunity.id}'
                ),
                'target_department': 'Marketing Department',
                'priority': 2,
                'task_type': 'content_creation',
            },
            required_permissions=[],
            is_active=True,
        )

        # Set department visibility
        try:
            sales_dept = Department.objects.get(name='Sales Department')
            trigger.visible_to_departments.add(sales_dept)  # Only Sales, not Marketing!
        except Department.DoesNotExist:
            pass


def reverse_update(apps, schema_editor):
    """Reverse the trigger update (optional - could delete or restore old config)"""
    # Leave trigger as-is on reverse; manual cleanup preferred
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('crm_extensions', '0014_add_deliverable_index'),
        ('api', '__latest__'),  # Need Department model
    ]

    operations = [
        migrations.RunPython(update_marketing_deliverable_trigger, reverse_update),
    ]
