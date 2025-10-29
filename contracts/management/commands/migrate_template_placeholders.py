from django.core.management.base import BaseCommand
from contracts.models import ContractTemplate


class Command(BaseCommand):
    help = 'Migrate template placeholders from year-based to range-based commission structure'

    def handle(self, *args, **options):
        """
        Update template placeholders:
        1. Remove commission.year1-5 placeholders (35 total)
        2. Remove company.* placeholders (10 total)
        3. Add commission.first_years.*, last_years.* placeholders (16 total)
        Note: Middle years are calculated but don't need placeholders in contract docs
        """

        # Find templates that need migration
        templates = ContractTemplate.objects.all()

        for template in templates:
            self.stdout.write(f"\nProcessing template: {template.name}")

            old_placeholders = template.placeholders or []
            new_placeholders = []

            # Placeholders to remove
            placeholders_to_remove = set()

            # Year-based commission placeholders to remove
            for year in range(1, 6):
                for share_type in ['concert', 'rights', 'merchandising', 'image_rights', 'ppd', 'emd', 'sync']:
                    placeholders_to_remove.add(f'commission.year{year}.{share_type}')

            # Company placeholders to remove (should be entity.* for counterparty or maincompany.* for HaHaHa Production)
            company_placeholders = [
                'company.name', 'company.registration_number', 'company.vat_number',
                'company.address', 'company.city', 'company.state', 'company.zip_code',
                'company.country', 'company.email', 'company.phone'
            ]
            placeholders_to_remove.update(company_placeholders)

            # Filter out old placeholders
            removed_count = 0
            for placeholder in old_placeholders:
                if isinstance(placeholder, str):
                    if placeholder in placeholders_to_remove:
                        removed_count += 1
                        self.stdout.write(self.style.WARNING(f"  Removing: {placeholder}"))
                    else:
                        new_placeholders.append(placeholder)
                elif isinstance(placeholder, dict):
                    # Object format placeholder
                    key = placeholder.get('key', '')
                    if key in placeholders_to_remove:
                        removed_count += 1
                        self.stdout.write(self.style.WARNING(f"  Removing: {key}"))
                    else:
                        new_placeholders.append(placeholder)

            # Add new range-based commission placeholders
            # Note: Only first_years and last_years appear in contract documents
            # Middle years are calculated automatically but not shown in contracts
            share_types = ['concert', 'rights', 'merchandising', 'image_rights', 'ppd', 'emd', 'sync']
            added_placeholders = []

            # Add first_years and last_years placeholders only
            for share_type in share_types:
                added_placeholders.append(f'commission.first_years.{share_type}')
                added_placeholders.append(f'commission.last_years.{share_type}')

            # Also add count placeholders
            added_placeholders.append('commission.first_years_count')
            added_placeholders.append('commission.last_years_count')

            # Check if already added
            existing_keys = {p if isinstance(p, str) else p.get('key') for p in new_placeholders}

            for placeholder_key in added_placeholders:
                if placeholder_key not in existing_keys:
                    new_placeholders.append(placeholder_key)
                    self.stdout.write(self.style.SUCCESS(f"  Adding: {placeholder_key}"))

            # Update template
            template.placeholders = new_placeholders
            template.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Updated {template.name}: "
                    f"removed {removed_count}, "
                    f"added {len(added_placeholders)}, "
                    f"total: {len(new_placeholders)}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Successfully migrated {templates.count()} template(s)"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "\n⚠️  IMPORTANT: You must update the Google Doc templates manually!"
            )
        )
        self.stdout.write(
            "Replace in your Google Docs:\n"
            "  Old: {{commission.year1.concert}}, {{commission.year2.concert}}, ...\n"
            "  New: {{commission.first_years.concert}}, {{commission.last_years.concert}}\n"
            "  Note: Middle years are calculated automatically - no placeholder needed\n"
        )
        self.stdout.write(
            "Also replace:\n"
            "  Old: {{company.name}}, {{company.email}}, ...\n"
            "  New: {{entity.name}}, {{entity.email}}, ... (for counterparty)\n"
            "   OR: {{maincompany.name}}, {{maincompany.email}}, ... (for HaHaHa Production)\n"
        )
