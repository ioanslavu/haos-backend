from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0008_rename_contracts_c_contrac_idx_contracts_c_contrac_0f719b_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='department',
            field=models.CharField(blank=True, choices=[('digital', 'Digital'), ('sales', 'Sales')], help_text='Owning department for access control', max_length=50, null=True),
        ),
        migrations.CreateModel(
            name='ContractTypePolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('guest', 'Guest'), ('administrator', 'Administrator'), ('digital_manager', 'Digital Manager'), ('digital_employee', 'Digital Employee'), ('sales_manager', 'Sales Manager'), ('sales_employee', 'Sales Employee')], db_index=True, max_length=50)),
                ('department', models.CharField(choices=[('digital', 'Digital'), ('sales', 'Sales')], db_index=True, max_length=50)),
                ('contract_type', models.CharField(choices=[('artist_master', 'Artist Master Agreement'), ('producer_service', 'Producer Service Agreement'), ('publishing_writer', 'Publishing Writer Agreement'), ('publishing_admin', 'Publishing Administration'), ('co_pub', 'Co-Publishing Agreement'), ('license_sync', 'Synchronization License'), ('co_label', 'Co-Label Agreement'), ('video_production', 'Video Production Agreement'), ('digital_dist', 'Digital Distribution Agreement')], db_index=True, max_length=30)),
                ('can_view', models.BooleanField(default=True)),
                ('can_publish', models.BooleanField(default=False)),
                ('can_send', models.BooleanField(default=False)),
                ('can_update', models.BooleanField(default=False)),
                ('can_delete', models.BooleanField(default=False)),
                ('can_regenerate', models.BooleanField(default=False)),
            ],
            options={
                'indexes': [models.Index(fields=['role', 'department'], name='contracts_c_role_dept_idx')],
                'unique_together': {('role', 'department', 'contract_type')},
            },
        ),
    ]

