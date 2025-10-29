from django.core.management.base import BaseCommand
from contracts.models import ContractTemplate


class Command(BaseCommand):
    help = 'Updates the placeholders for the artist contract template'

    def handle(self, *args, **options):
        # Find the template by name or ID
        template_name = "CONTRACT DE PRODUCȚIE, IMPRESARIAT ȘI MANAGEMENT ARTISTIC"

        try:
            template = ContractTemplate.objects.get(name=template_name)
        except ContractTemplate.DoesNotExist:
            # Try by ID if name doesn't match
            try:
                template = ContractTemplate.objects.get(id=2)
            except ContractTemplate.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'Template "{template_name}" not found. Please check the template name or ID.'
                    )
                )
                return

        # Define all the contextual placeholders
        new_placeholders = [
            # Entity/Person placeholders
            'person.full_name',
            'person.first_name',
            'person.last_name',
            'artist.stage_name',
            'person.nationality',
            'person.email',
            'person.phone',
            'person.shares',
            'person.address',
            'person.city',
            'person.state',
            'person.zip_code',
            'person.country',

            # Banking placeholders
            'bank.iban',
            'bank.name',
            'bank.branch',

            # ID placeholders
            'id.cnp',
            'id.series',
            'id.number',
            'id.issued_by',
            'id.issued_date',
            'id.expiry_date',
            'person.birth_date',
            'person.birth_place',

            # Contract terms placeholders
            'contract.duration_years',
            'contract.notice_period_days',
            'contract.auto_renewal',
            'contract.auto_renewal_years',
            'contract.minimum_launches_per_year',
            'contract.max_investment_per_song',
            'contract.max_investment_per_year',
            'contract.penalty_amount',
            'contract.currency',
            'contract.start_date',
            'contract.end_date',
            'contract.special_terms',

            # Commission placeholders for Year 1
            'commission.year1.concert',
            'commission.year1.rights',
            'commission.year1.merchandising',
            'commission.year1.image_rights',
            'commission.year1.ppd',
            'commission.year1.emd',
            'commission.year1.sync',

            # Commission placeholders for Year 2
            'commission.year2.concert',
            'commission.year2.rights',
            'commission.year2.merchandising',
            'commission.year2.image_rights',
            'commission.year2.ppd',
            'commission.year2.emd',
            'commission.year2.sync',

            # Commission placeholders for Year 3
            'commission.year3.concert',
            'commission.year3.rights',
            'commission.year3.merchandising',
            'commission.year3.image_rights',
            'commission.year3.ppd',
            'commission.year3.emd',
            'commission.year3.sync',

            # Commission placeholders for Year 4
            'commission.year4.concert',
            'commission.year4.rights',
            'commission.year4.merchandising',
            'commission.year4.image_rights',
            'commission.year4.ppd',
            'commission.year4.emd',
            'commission.year4.sync',

            # Commission placeholders for Year 5
            'commission.year5.concert',
            'commission.year5.rights',
            'commission.year5.merchandising',
            'commission.year5.image_rights',
            'commission.year5.ppd',
            'commission.year5.emd',
            'commission.year5.sync',

            # Company placeholders (for PJ entities)
            'company.name',
            'company.registration_number',
            'company.vat_number',
            'company.address',
            'company.city',
            'company.state',
            'company.zip_code',
            'company.country',
            'company.email',
            'company.phone',

            # Additional contract metadata
            'contract.number',
            'contract.date',
            'contract.year',
            'today.date',
            'today.day',
            'today.month',
            'today.year',
        ]

        # Update the template placeholders
        template.placeholders = new_placeholders
        template.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated template "{template.name}" with {len(new_placeholders)} placeholders'
            )
        )

        # Print a sample of the placeholders for verification
        self.stdout.write('\nSample placeholders:')
        for placeholder in new_placeholders[:10]:
            self.stdout.write(f'  - {{{{placeholder}}}}')
        self.stdout.write(f'  ... and {len(new_placeholders) - 10} more')

        # Print instructions for updating the Google Doc
        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  Remember to update the actual Google Doc template with these placeholders!'
            )
        )
        self.stdout.write(
            'Replace the existing placeholders in the Google Doc with the contextual ones above.'
        )
        self.stdout.write(
            'For example: {{artist_name}} → {{artist.stage_name}}, {{cnp}} → {{id.cnp}}, etc.'
        )