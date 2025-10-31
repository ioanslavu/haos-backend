# Generated migration for adding alias_name field to Entity model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('identity', '0015_add_client_profile_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='entity',
            name='alias_name',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Alternative name or alias for the entity',
                max_length=255,
                null=True
            ),
        ),
    ]
