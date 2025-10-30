"""
ONE-TIME SCRIPT: Restore deleted contract template to database

This script recreates the "CONTRACT DE PRODUCȚIE, IMPRESARIAT ȘI MANAGEMENT ARTISTIC"
template that was accidentally deleted.

Usage:
    python contracts/TEMP_restore_deleted_template.py

After use, this file can be safely deleted.

Author: Claude Code
Date: 2025-10-30
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/home/ioan/projects/HaOS/stack/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contracts.models import ContractTemplate, ContractTemplateVersion
from django.contrib.auth import get_user_model

User = get_user_model()


def restore_template():
    """Restore the deleted CONTRACT DE PRODUCȚIE template."""

    print("="*80)
    print("RESTORING DELETED CONTRACT TEMPLATE")
    print("="*80)
    print()

    # Template information from conversation history
    template_data = {
        'name': 'CONTRACT DE PRODUCȚIE, IMPRESARIAT ȘI MANAGEMENT ARTISTIC',
        'description': 'Contract de producție, impresariat și management artistic [360] - Artist Master Agreement',
        'series': 'HAHM',  # Series identifier for contract numbering

        # NEW version with all placeholders (the one we just created)
        'gdrive_template_file_id': '1j1fvG7ybv2Rvkk0t7rIkSOtwYnXPomBcqcfYSMhoMRA',

        # Shared drive output folder (same as other templates)
        'gdrive_output_folder_id': '1TrdRta7xLadFV3vH7-tWZhFLo8ptJvAK',

        # Placeholders definition based on the contract structure
        'placeholders': [
            # Main company placeholders
            {"key": "maincompany.name", "label": "Company Name", "type": "text", "required": True},
            {"key": "maincompany.address", "label": "Company Address", "type": "text", "required": True},
            {"key": "maincompany.registration_number", "label": "Registration Number", "type": "text", "required": True},
            {"key": "maincompany.cif", "label": "CIF", "type": "text", "required": True},
            {"key": "maincompany.iban", "label": "IBAN", "type": "text", "required": True},
            {"key": "maincompany.bank_name", "label": "Bank Name", "type": "text", "required": True},
            {"key": "maincompany.admin_name", "label": "Administrator Name", "type": "text", "required": True},
            {"key": "maincompany.admin_role", "label": "Administrator Role", "type": "text", "required": True},

            # Entity placeholders (artist/counterparty)
            {"key": "entity.full_name", "label": "Artist Full Name", "type": "text", "required": True},
            {"key": "entity.address", "label": "Artist Address", "type": "text", "required": True},
            {"key": "entity.city", "label": "Artist City", "type": "text", "required": True},
            {"key": "entity.identification_full", "label": "Artist ID Full", "type": "text", "required": True},
            {"key": "entity.identification_short", "label": "Artist ID Short", "type": "text", "required": True},
            {"key": "entity.iban", "label": "Artist IBAN", "type": "text", "required": False},
            {"key": "entity.bank_name", "label": "Artist Bank", "type": "text", "required": False},
            {"key": "entity.email", "label": "Artist Email", "type": "email", "required": False},
            {"key": "entity.phone", "label": "Artist Phone", "type": "text", "required": False},

            # Gender placeholder
            {"key": "entity.gender", "label": "Gender (m/f)", "type": "text", "required": True},

            # Contract terms
            {"key": "contract_duration_years", "label": "Contract Duration (years)", "type": "number", "required": True},
            {"key": "notice_period_days", "label": "Notice Period (days)", "type": "number", "required": True},

            # Investment terms
            {"key": "minimum_launches_per_year", "label": "Minimum Launches Per Year", "type": "number", "required": True},
            {"key": "max_investment_per_song", "label": "Max Investment Per Song (EUR)", "type": "number", "required": True},
            {"key": "max_investment_per_year", "label": "Max Investment Per Year (EUR)", "type": "number", "required": True},

            # Commission structure - Concert
            {"key": "concert_uniform", "label": "Concert Uniform Rate (0 or 1)", "type": "number", "required": True},
            {"key": "commission.concert.uniform", "label": "Concert Commission (uniform %)", "type": "number", "required": False},
            {"key": "concert_first_years", "label": "Concert First Years Count", "type": "number", "required": False},
            {"key": "concert_last_years", "label": "Concert Last Years Count", "type": "number", "required": False},
            {"key": "commission.concert.first_years", "label": "Concert Commission First Years (%)", "type": "number", "required": False},
            {"key": "commission.concert.last_years", "label": "Concert Commission Last Years (%)", "type": "number", "required": False},

            # Commission structure - PPD
            {"key": "has_ppd_rights", "label": "Has PPD Rights (0 or 1)", "type": "number", "required": False},
            {"key": "ppd_uniform", "label": "PPD Uniform Rate (0 or 1)", "type": "number", "required": False},
            {"key": "commission.ppd.uniform", "label": "PPD Commission (uniform %)", "type": "number", "required": False},
            {"key": "ppd_first_years", "label": "PPD First Years Count", "type": "number", "required": False},
            {"key": "ppd_last_years", "label": "PPD Last Years Count", "type": "number", "required": False},
            {"key": "commission.ppd.first_years", "label": "PPD Commission First Years (%)", "type": "number", "required": False},
            {"key": "commission.ppd.last_years", "label": "PPD Commission Last Years (%)", "type": "number", "required": False},

            # Commission structure - EMD
            {"key": "has_emd_rights", "label": "Has EMD Rights (0 or 1)", "type": "number", "required": False},
            {"key": "emd_uniform", "label": "EMD Uniform Rate (0 or 1)", "type": "number", "required": False},
            {"key": "commission.emd.uniform", "label": "EMD Commission (uniform %)", "type": "number", "required": False},
            {"key": "emd_first_years", "label": "EMD First Years Count", "type": "number", "required": False},
            {"key": "emd_last_years", "label": "EMD Last Years Count", "type": "number", "required": False},
            {"key": "commission.emd.first_years", "label": "EMD Commission First Years (%)", "type": "number", "required": False},
            {"key": "commission.emd.last_years", "label": "EMD Commission Last Years (%)", "type": "number", "required": False},

            # Commission structure - Sync
            {"key": "has_sync_rights", "label": "Has Sync Rights (0 or 1)", "type": "number", "required": False},
            {"key": "sync_uniform", "label": "Sync Uniform Rate (0 or 1)", "type": "number", "required": False},
            {"key": "commission.sync.uniform", "label": "Sync Commission (uniform %)", "type": "number", "required": False},
            {"key": "sync_first_years", "label": "Sync First Years Count", "type": "number", "required": False},
            {"key": "sync_last_years", "label": "Sync Last Years Count", "type": "number", "required": False},
            {"key": "commission.sync.first_years", "label": "Sync Commission First Years (%)", "type": "number", "required": False},
            {"key": "commission.sync.last_years", "label": "Sync Commission Last Years (%)", "type": "number", "required": False},

            # Commission structure - Merchandising
            {"key": "has_merchandising_rights", "label": "Has Merchandising Rights (0 or 1)", "type": "number", "required": False},
            {"key": "merchandising_uniform", "label": "Merchandising Uniform Rate (0 or 1)", "type": "number", "required": False},
            {"key": "commission.merchandising.uniform", "label": "Merchandising Commission (uniform %)", "type": "number", "required": False},
            {"key": "merchandising_first_years", "label": "Merchandising First Years Count", "type": "number", "required": False},
            {"key": "merchandising_last_years", "label": "Merchandising Last Years Count", "type": "number", "required": False},
            {"key": "commission.merchandising.first_years", "label": "Merchandising Commission First Years (%)", "type": "number", "required": False},
            {"key": "commission.merchandising.last_years", "label": "Merchandising Commission Last Years (%)", "type": "number", "required": False},

            # Date placeholder
            {"key": "today", "label": "Today's Date", "type": "date", "required": True},
        ],

        'is_active': True,
    }

    # Check if template already exists
    existing = ContractTemplate.objects.filter(series=template_data['series']).first()
    if existing:
        print(f"❌ Template with series '{template_data['series']}' already exists!")
        print(f"   ID: {existing.id}")
        print(f"   Name: {existing.name}")
        print(f"   Created: {existing.created_at}")
        print()
        print("If you want to update it, delete it first or modify the series identifier.")
        return

    # Get the first superuser as created_by (or None)
    creator = User.objects.filter(is_superuser=True).first()

    # Create the template
    print(f"Creating template: {template_data['name']}")
    print(f"Series: {template_data['series']}")
    print(f"Google Drive File ID: {template_data['gdrive_template_file_id']}")
    print(f"Output Folder ID: {template_data['gdrive_output_folder_id']}")
    print(f"Placeholders: {len(template_data['placeholders'])} defined")
    print()

    template = ContractTemplate.objects.create(
        name=template_data['name'],
        description=template_data['description'],
        series=template_data['series'],
        gdrive_template_file_id=template_data['gdrive_template_file_id'],
        placeholders=template_data['placeholders'],
        gdrive_output_folder_id=template_data['gdrive_output_folder_id'],
        is_active=template_data['is_active'],
        created_by=creator
    )

    print("✅ Template created successfully!")
    print(f"   ID: {template.id}")
    print(f"   Name: {template.name}")
    print(f"   Series: {template.series}")
    print(f"   Active: {template.is_active}")
    print()

    # Create initial version
    print("Creating initial template version...")
    version = ContractTemplateVersion.objects.create(
        template=template,
        version_number=1,
        gdrive_file_id=template_data['gdrive_template_file_id'],
        placeholders_snapshot=template_data['placeholders'],
        change_description='Initial version with full conditional sections and phrase placeholders',
        created_by=creator
    )

    print("✅ Version created successfully!")
    print(f"   Version: {version.version_number}")
    print(f"   Description: {version.change_description}")
    print()

    print("="*80)
    print("SUCCESS! Template restored to database.")
    print("="*80)
    print()
    print("You can now:")
    print("1. Use this template to generate contracts")
    print("2. Delete this script: rm contracts/TEMP_restore_deleted_template.py")
    print()


if __name__ == '__main__':
    try:
        restore_template()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
