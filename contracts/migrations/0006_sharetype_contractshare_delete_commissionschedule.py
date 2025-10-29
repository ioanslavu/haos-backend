# Generated migration for ShareType, ContractShare, and removal of Entity.shares and CommissionSchedule

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


def seed_share_types(apps, schema_editor):
    """Seed initial share types for artist contracts."""
    ShareType = apps.get_model('contracts', 'ShareType')

    share_types = [
        {
            'code': 'concert_commission',
            'name': 'Concert Commission',
            'description': 'Commission percentage from concert/live performance revenue',
            'placeholder_keys': ['commission.year_{year}.concerts', 'concert_commission'],
            'contract_types': ['artist_master'],
        },
        {
            'code': 'rights_percentage',
            'name': 'Connected Rights Percentage',
            'description': 'Percentage from connected/neighboring rights',
            'placeholder_keys': ['commission.year_{year}.rights', 'rights_percentage'],
            'contract_types': ['artist_master'],
        },
        {
            'code': 'merchandising_percentage',
            'name': 'Merchandising Percentage',
            'description': 'Percentage from merchandising revenue',
            'placeholder_keys': ['commission.year_{year}.merchandising', 'merchandising_percentage'],
            'contract_types': ['artist_master'],
        },
        {
            'code': 'image_rights_percentage',
            'name': 'Image Rights Percentage',
            'description': 'Percentage from image/likeness rights',
            'placeholder_keys': ['commission.year_{year}.image', 'image_rights_percentage'],
            'contract_types': ['artist_master'],
        },
        {
            'code': 'ppd_percentage',
            'name': 'PPD Percentage',
            'description': 'Percentage from physical product distribution (PPD)',
            'placeholder_keys': ['commission.year_{year}.ppd', 'ppd_percentage'],
            'contract_types': ['artist_master'],
        },
        {
            'code': 'emd_percentage',
            'name': 'EMD Percentage',
            'description': 'Percentage from electronic/digital music distribution (EMD)',
            'placeholder_keys': ['commission.year_{year}.emd', 'emd_percentage'],
            'contract_types': ['artist_master'],
        },
        {
            'code': 'sync_percentage',
            'name': 'Synchronization Percentage',
            'description': 'Percentage from synchronization licensing',
            'placeholder_keys': ['commission.year_{year}.sync', 'sync_percentage'],
            'contract_types': ['artist_master'],
        },
        # Future share types (not yet used but ready for future contracts)
        {
            'code': 'master_share',
            'name': 'Master Share',
            'description': 'Ownership percentage of master recording',
            'placeholder_keys': ['master_share', 'artist.master_share'],
            'contract_types': ['artist_master', 'producer_service', 'co_prod'],
        },
        {
            'code': 'writer_share',
            'name': 'Writer Share',
            'description': 'Composition/publishing writer share percentage',
            'placeholder_keys': ['writer_share', 'writer.share'],
            'contract_types': ['publishing_writer'],
        },
        {
            'code': 'publisher_share',
            'name': 'Publisher Share',
            'description': 'Composition/publishing publisher share percentage',
            'placeholder_keys': ['publisher_share', 'publisher.share'],
            'contract_types': ['publishing_admin', 'co_pub'],
        },
        {
            'code': 'producer_points',
            'name': 'Producer Points',
            'description': 'Producer points from master recordings',
            'placeholder_keys': ['producer_points', 'producer.points'],
            'contract_types': ['producer_service'],
        },
    ]

    for share_type_data in share_types:
        ShareType.objects.create(**share_type_data)


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0005_contractterms_commissionschedule'),
        ('identity', '0003_entity_bank_branch_entity_bank_name_entity_iban_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create ShareType model
        migrations.CreateModel(
            name='ShareType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(
                    db_index=True,
                    help_text='Machine-readable share type code',
                    max_length=64,
                    unique=True
                )),
                ('name', models.CharField(help_text='Human-readable share type name', max_length=120)),
                ('description', models.TextField(blank=True, help_text='Description of this share type')),
                ('placeholder_keys', models.JSONField(
                    default=list,
                    help_text='List of template placeholder keys for this share type. Use {year} for year-based placeholders.'
                )),
                ('contract_types', models.JSONField(
                    blank=True,
                    default=list,
                    help_text='List of contract types that use this share type (empty = all types)'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Share Type',
                'verbose_name_plural': 'Share Types',
                'ordering': ['code'],
            },
        ),

        # Create ContractShare model
        migrations.CreateModel(
            name='ContractShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DecimalField(
                    decimal_places=4,
                    help_text='Share value (e.g., 15.0000 for 15%)',
                    max_digits=8,
                    validators=[MinValueValidator(Decimal('0.0000'))]
                )),
                ('unit', models.CharField(
                    choices=[('percent', 'Percentage'), ('points', 'Points'), ('flat', 'Flat Amount')],
                    default='percent',
                    help_text='Unit of measurement for the value',
                    max_length=16
                )),
                ('valid_from', models.DateField(help_text='Start date for this share rate')),
                ('valid_to', models.DateField(blank=True, help_text='End date (null = open-ended)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contract', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shares',
                    to='contracts.contract'
                )),
                ('share_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='contract_shares',
                    to='contracts.sharetype'
                )),
            ],
            options={
                'verbose_name': 'Contract Share',
                'verbose_name_plural': 'Contract Shares',
                'ordering': ['valid_from', 'share_type__code'],
            },
        ),

        # Add indexes to ContractShare
        migrations.AddIndex(
            model_name='contractshare',
            index=models.Index(fields=['contract', 'share_type'], name='contracts_c_contrac_idx'),
        ),
        migrations.AddIndex(
            model_name='contractshare',
            index=models.Index(fields=['share_type', 'valid_from'], name='contracts_c_share_t_idx'),
        ),
        migrations.AddIndex(
            model_name='contractshare',
            index=models.Index(fields=['valid_from', 'valid_to'], name='contracts_c_valid_f_idx'),
        ),

        # Seed initial share types
        migrations.RunPython(seed_share_types, migrations.RunPython.noop),

        # Delete CommissionSchedule model
        migrations.DeleteModel(
            name='CommissionSchedule',
        ),
    ]
