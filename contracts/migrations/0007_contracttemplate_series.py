# Generated migration for adding series field to ContractTemplate

from django.db import migrations, models


def assign_default_series(apps, schema_editor):
    """Assign default series to existing templates."""
    ContractTemplate = apps.get_model('contracts', 'ContractTemplate')

    # Assign sequential series numbers to existing templates
    for idx, template in enumerate(ContractTemplate.objects.all().order_by('id'), start=1):
        template.series = str(idx)
        template.save()


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0006_sharetype_contractshare_delete_commissionschedule'),
    ]

    operations = [
        # Add series field as nullable first
        migrations.AddField(
            model_name='contracttemplate',
            name='series',
            field=models.CharField(
                max_length=50,
                null=True,
                blank=True,
                help_text='Series identifier for contract numbering (e.g., 1, 2, A, 2025). Must be unique.'
            ),
        ),
        # Populate series for existing templates
        migrations.RunPython(assign_default_series, reverse_code=migrations.RunPython.noop),
        # Make series non-nullable and unique
        migrations.AlterField(
            model_name='contracttemplate',
            name='series',
            field=models.CharField(
                max_length=50,
                unique=True,
                help_text='Series identifier for contract numbering (e.g., 1, 2, A, 2025). Must be unique.'
            ),
        ),
    ]
