"""
Seed command for Artist Sales CRM.
Creates comprehensive seed data for testing and development.

Usage:
    python manage.py seed_artist_sales
    python manage.py seed_artist_sales --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

from artist_sales.models import (
    Brief, Opportunity, Proposal, ProposalArtist,
    DeliverablePack, DeliverablePackItem, UsageTerms,
    Deal, DealArtist, DealDeliverable, Approval
)
from identity.models import Entity, EntityRole, ContactPerson
from api.models import Department

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed artist sales data for development and testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing artist sales data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing artist sales data...'))
            self.clear_data()
            self.stdout.write(self.style.SUCCESS('✓ Cleared'))

        self.stdout.write(self.style.SUCCESS('Starting artist sales seed...'))

        # Get or create required objects
        self.user = self.get_or_create_user()
        self.department = self.get_or_create_department()

        # Create entities
        self.stdout.write('Creating entities...')
        self.brands = self.create_brands()
        self.agencies = self.create_agencies()
        self.artists = self.create_artists()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.brands)} brands, {len(self.agencies)} agencies, {len(self.artists)} artists'))

        # Create contact persons
        self.stdout.write('Creating contact persons...')
        self.create_contact_persons()
        self.stdout.write(self.style.SUCCESS('✓ Created contact persons'))

        # Create deliverable packs
        self.stdout.write('Creating deliverable packs...')
        self.packs = self.create_deliverable_packs()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.packs)} deliverable packs'))

        # Create usage terms
        self.stdout.write('Creating usage terms...')
        self.terms = self.create_usage_terms()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.terms)} usage terms templates'))

        # Create briefs
        self.stdout.write('Creating briefs...')
        self.briefs = self.create_briefs()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.briefs)} briefs'))

        # Create opportunities
        self.stdout.write('Creating opportunities...')
        self.opportunities = self.create_opportunities()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.opportunities)} opportunities'))

        # Create proposals
        self.stdout.write('Creating proposals...')
        self.proposals = self.create_proposals()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.proposals)} proposals'))

        # Create deals
        self.stdout.write('Creating deals...')
        self.deals = self.create_deals()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.deals)} deals'))

        # Create approvals
        self.stdout.write('Creating approvals...')
        self.approvals = self.create_approvals()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(self.approvals)} approvals'))

        self.stdout.write(self.style.SUCCESS('\n🎉 Artist sales seed completed successfully!'))
        self.print_summary()

    def clear_data(self):
        """Clear all artist sales data"""
        Approval.objects.all().delete()
        DealDeliverable.objects.all().delete()
        DealArtist.objects.all().delete()
        Deal.objects.all().delete()
        ProposalArtist.objects.all().delete()
        Proposal.objects.all().delete()
        Opportunity.objects.all().delete()
        Brief.objects.all().delete()
        DeliverablePackItem.objects.all().delete()
        DeliverablePack.objects.all().delete()
        UsageTerms.objects.all().delete()

    def get_or_create_user(self):
        """Get or create a user for created_by fields"""
        user = User.objects.filter(is_active=True).first()
        if not user:
            user = User.objects.create_user(
                username='admin',
                email='admin@hahahaproduction.com',
                password='admin123'
            )
        return user

    def get_or_create_department(self):
        """Get or create a department"""
        dept = Department.objects.first()
        if not dept:
            dept = Department.objects.create(
                code='artist_sales',
                name='Artist Sales',
                description='Artist sales and image rights department'
            )
        return dept

    def create_brands(self):
        """Create brand entities"""
        brands_data = [
            {'name': 'Coca-Cola Romania', 'category': 'Beverage'},
            {'name': 'Samsung Electronics', 'category': 'Technology'},
            {'name': 'Nike Romania', 'category': 'Fashion'},
            {'name': 'Vodafone Romania', 'category': 'Telecom'},
            {'name': 'eMAG', 'category': 'E-commerce'},
            {'name': 'Kaufland Romania', 'category': 'Retail'},
            {'name': 'Heineken Romania', 'category': 'Beverage'},
            {'name': 'Decathlon Romania', 'category': 'Sports'},
        ]

        brands = []
        for data in brands_data:
            entity, created = Entity.objects.get_or_create(
                display_name=data['name'],
                kind='PJ',
                defaults={
                    'created_by': self.user,
                    'email': f"contact@{data['name'].lower().replace(' ', '')}.com",
                    'phone': f'+4021{random.randint(3000000, 3999999)}',
                    'address': f'Strada {data["name"]} nr. {random.randint(1, 100)}',
                    'city': random.choice(['București', 'Cluj-Napoca', 'Timișoara']),
                    'country': 'Romania',
                }
            )
            # Add brand role
            EntityRole.objects.get_or_create(entity=entity, role='brand')
            brands.append(entity)

        return brands

    def create_agencies(self):
        """Create agency entities"""
        agencies_data = [
            {'name': 'Publicis Romania', 'holding': 'Publicis Groupe'},
            {'name': 'McCann Bucharest', 'holding': 'McCann Worldgroup'},
            {'name': 'Leo Burnett Romania', 'holding': 'Publicis Groupe'},
            {'name': 'Ogilvy Romania', 'holding': 'WPP'},
        ]

        agencies = []
        for data in agencies_data:
            entity, created = Entity.objects.get_or_create(
                display_name=data['name'],
                kind='PJ',
                defaults={
                    'holding': data.get('holding'),
                    'created_by': self.user,
                    'email': f"contact@{data['name'].lower().replace(' ', '')}.com",
                    'phone': f'+4021{random.randint(3000000, 3999999)}',
                    'address': f'Bulevardul {data["name"]} nr. {random.randint(1, 100)}',
                    'city': 'București',
                    'country': 'Romania',
                }
            )
            # Add client role
            EntityRole.objects.get_or_create(entity=entity, role='client')
            agencies.append(entity)

        return agencies

    def create_artists(self):
        """Create artist entities"""
        artists_data = [
            {'name': 'Smiley', 'stage_name': 'Smiley', 'tier': 'A'},
            {'name': 'INNA', 'stage_name': 'INNA', 'tier': 'A'},
            {'name': 'Carla\'s Dreams', 'stage_name': 'Carla\'s Dreams', 'tier': 'A'},
            {'name': 'The Motans', 'stage_name': 'The Motans', 'tier': 'B'},
            {'name': 'Irina Rimes', 'stage_name': 'Irina Rimes', 'tier': 'B'},
            {'name': 'Connect-R', 'stage_name': 'Connect-R', 'tier': 'B'},
            {'name': 'Delia', 'stage_name': 'Delia', 'tier': 'B'},
            {'name': 'Antonia', 'stage_name': 'Antonia', 'tier': 'C'},
            {'name': 'Corina', 'stage_name': 'Corina', 'tier': 'C'},
            {'name': 'Nicole Cherry', 'stage_name': 'Nicole Cherry', 'tier': 'C'},
        ]

        artists = []
        for data in artists_data:
            entity, created = Entity.objects.get_or_create(
                display_name=data['name'],
                kind='PF',
                defaults={
                    'stage_name': data['stage_name'],
                    'rate_tier': data['tier'],
                    'first_name': data['name'].split()[0],
                    'last_name': data['name'].split()[-1] if ' ' in data['name'] else '',
                    'nationality': 'Romanian',
                    'created_by': self.user,
                    'email': f"{data['stage_name'].lower().replace(' ', '')}@artist.ro",
                    'phone': f'+4074{random.randint(0000000, 9999999):07d}',
                }
            )
            # Add artist role
            EntityRole.objects.get_or_create(
                entity=entity,
                role='artist',
                defaults={'primary_role': True, 'is_internal': True}
            )
            artists.append(entity)

        return artists

    def create_contact_persons(self):
        """Create contact persons for brands and agencies"""
        roles = ['marketing', 'brand', 'pr', 'a&r']

        for entity in self.brands + self.agencies:
            # Create 1-2 contacts per entity
            for i in range(random.randint(1, 2)):
                ContactPerson.objects.get_or_create(
                    entity=entity,
                    name=f"{random.choice(['Ana', 'Maria', 'Alexandru', 'Andrei', 'Elena', 'Mihai'])} {random.choice(['Popescu', 'Ionescu', 'Popa', 'Radu', 'Constantin'])}",
                    defaults={
                        'role': random.choice(roles),
                        'engagement_stage': random.choice(['active', 'prospect', 'partner']),
                        'sentiment': random.choice(['supportive', 'professional', 'friendly']),
                        'notes': f'Key contact for {entity.display_name}',
                    }
                )

    def create_deliverable_packs(self):
        """Create deliverable pack templates"""
        packs_data = [
            {
                'name': 'Standard Social Media Package',
                'description': 'Basic social media deliverables for Instagram and TikTok',
                'items': [
                    {'type': 'ig_post', 'qty': 2},
                    {'type': 'ig_story', 'qty': 3},
                    {'type': 'ig_reel', 'qty': 1},
                ]
            },
            {
                'name': 'TikTok Campaign Bundle',
                'description': 'Comprehensive TikTok campaign package',
                'items': [
                    {'type': 'tiktok_video', 'qty': 4},
                    {'type': 'ig_reel', 'qty': 2},
                ]
            },
            {
                'name': 'YouTube Integration',
                'description': 'YouTube content and shorts',
                'items': [
                    {'type': 'youtube_video', 'qty': 1},
                    {'type': 'youtube_short', 'qty': 3},
                ]
            },
            {
                'name': 'ATL Campaign (TV + Digital)',
                'description': 'Above-the-line campaign with TVC and digital',
                'items': [
                    {'type': 'tvc', 'qty': 1},
                    {'type': 'digital_banner', 'qty': 5},
                    {'type': 'ig_post', 'qty': 2},
                ]
            },
            {
                'name': 'Event Appearance',
                'description': 'Live event appearance with social coverage',
                'items': [
                    {'type': 'event', 'qty': 1},
                    {'type': 'ig_story', 'qty': 5},
                    {'type': 'ig_post', 'qty': 2},
                ]
            },
        ]

        packs = []
        for data in packs_data:
            pack, created = DeliverablePack.objects.get_or_create(
                name=data['name'],
                defaults={'description': data['description'], 'is_active': True}
            )

            # Create items
            for item_data in data['items']:
                DeliverablePackItem.objects.get_or_create(
                    pack=pack,
                    deliverable_type=item_data['type'],
                    defaults={'quantity': item_data['qty']}
                )

            packs.append(pack)

        return packs

    def create_usage_terms(self):
        """Create usage terms templates"""
        terms_data = [
            {
                'name': 'Digital Only - 12 months',
                'scope': ['digital'],
                'territories': ['RO'],
                'duration_days': 365,
                'exclusivity_category': '',
                'buyout': False,
            },
            {
                'name': 'Social Media - 6 months (CEE)',
                'scope': ['digital'],
                'territories': ['RO', 'BG', 'HU', 'CZ', 'PL'],
                'duration_days': 180,
                'exclusivity_category': '',
                'buyout': False,
            },
            {
                'name': 'ATL + BTL - 24 months (Romania)',
                'scope': ['atl', 'btl', 'digital'],
                'territories': ['RO'],
                'duration_days': 730,
                'exclusivity_category': 'Beverage',
                'exclusivity_days': 730,
                'buyout': False,
            },
            {
                'name': 'Global Rights - Perpetual Buyout',
                'scope': ['global'],
                'territories': ['GLOBAL'],
                'duration_days': 36500,  # 100 years
                'exclusivity_category': '',
                'buyout': True,
            },
            {
                'name': 'OOH + Packaging - 18 months',
                'scope': ['ooh', 'packaging'],
                'territories': ['RO'],
                'duration_days': 540,
                'exclusivity_category': '',
                'buyout': False,
            },
            {
                'name': 'Broadcast (TV + Radio) - 12 months',
                'scope': ['broadcast'],
                'territories': ['RO', 'MD'],
                'duration_days': 365,
                'exclusivity_category': 'Automotive',
                'exclusivity_days': 365,
                'buyout': False,
            },
            {
                'name': 'Digital + In-Store - 6 months',
                'scope': ['digital', 'in_store'],
                'territories': ['RO'],
                'duration_days': 180,
                'exclusivity_category': '',
                'buyout': False,
            },
        ]

        terms = []
        for data in terms_data:
            term, created = UsageTerms.objects.get_or_create(
                name=data['name'],
                defaults={
                    'usage_scope': data['scope'],
                    'territories': data['territories'],
                    'usage_duration_days': data['duration_days'],
                    'exclusivity_category': data.get('exclusivity_category', ''),
                    'exclusivity_duration_days': data.get('exclusivity_days'),
                    'buyout': data['buyout'],
                    'is_template': True,
                    'extensions_allowed': not data['buyout'],
                }
            )
            terms.append(term)

        return terms

    def create_briefs(self):
        """Create briefs with various statuses"""
        statuses = ['new', 'qualified', 'pitched', 'lost', 'won']
        channels_options = [
            ['Paid Social', 'Instagram', 'TikTok'],
            ['TV', 'Radio', 'Digital'],
            ['OOH', 'Print', 'Digital'],
            ['Owned Media', 'Website', 'Social'],
        ]

        briefs = []
        for i in range(10):
            account = random.choice(self.brands + self.agencies)
            contact = account.contact_persons.first()

            status = random.choice(statuses)
            days_ago = random.randint(5, 60)

            brief = Brief.objects.create(
                account=account,
                contact_person=contact,
                department=self.department,
                created_by=self.user,
                campaign_title=f"{account.display_name} - {random.choice(['Summer Campaign', 'Launch Event', 'Brand Awareness', 'Product Launch', 'Holiday Special'])} {i+1}",
                brand_category=random.choice(['Beverage', 'Technology', 'Fashion', 'Telecom', 'E-commerce', 'Retail']),
                objectives=f"Drive brand awareness and engagement among 18-35 demographic.\nIncrease product consideration and trial.\nGenerate social media buzz and viral content.",
                target_audience="Young adults 18-35, urban, tech-savvy, active on social media",
                channels=random.choice(channels_options),
                timing_start=timezone.now().date() + timedelta(days=random.randint(14, 90)),
                timing_end=timezone.now().date() + timedelta(days=random.randint(120, 200)),
                budget_range_min=Decimal(random.choice([5000, 10000, 15000, 20000])),
                budget_range_max=Decimal(random.choice([30000, 50000, 75000, 100000])),
                currency='EUR',
                must_haves="Artist must have verified Instagram account\nContent must align with brand values\nDeliverables must be ready by campaign start date",
                nice_to_have="TikTok presence\nPrevious brand collaboration experience",
                brief_status=status,
                sla_due_date=timezone.now().date() + timedelta(days=7) if status == 'new' else None,
                notes=f"Brief received from {contact.name if contact else 'client'}" if contact else "",
            )
            brief.created_at = timezone.now() - timedelta(days=days_ago)
            brief.save(update_fields=['created_at'])

            briefs.append(brief)

        return briefs

    def create_opportunities(self):
        """Create opportunities linked to briefs"""
        stages = ['qualified', 'proposal', 'shortlist', 'negotiation', 'contract_sent', 'po_received', 'completed', 'closed_lost']

        opportunities = []

        # Some briefs convert to opportunities
        for brief in random.sample(self.briefs, 8):
            stage = random.choice(stages)
            days_ago = random.randint(1, 45)

            opp = Opportunity.objects.create(
                brief=brief,
                account=brief.account,
                owner_user=self.user,
                department=self.department,
                created_by=self.user,
                opp_name=brief.campaign_title,
                stage=stage,
                amount_expected=Decimal(random.randint(20000, 80000)),
                currency='EUR',
                probability_percent=self.get_probability_for_stage(stage),
                expected_close_date=timezone.now().date() + timedelta(days=random.randint(15, 60)),
                actual_close_date=timezone.now().date() if stage in ['completed', 'closed_lost'] else None,
                next_step=self.get_next_step_for_stage(stage),
                lost_reason="Client chose competitor" if stage == 'closed_lost' else "",
                notes=f"Opportunity from brief {brief.campaign_title}",
            )
            opp.created_at = timezone.now() - timedelta(days=days_ago)
            opp.save(update_fields=['created_at'])

            opportunities.append(opp)

        # Some standalone opportunities
        for i in range(7):
            account = random.choice(self.brands + self.agencies)
            stage = random.choice(stages)
            days_ago = random.randint(1, 40)

            opp = Opportunity.objects.create(
                account=account,
                owner_user=self.user,
                department=self.department,
                created_by=self.user,
                opp_name=f"{account.display_name} - {random.choice(['Q2 Campaign', 'Brand Partnership', 'Influencer Deal', 'Launch Campaign'])} {i+1}",
                stage=stage,
                amount_expected=Decimal(random.randint(15000, 90000)),
                currency='EUR',
                probability_percent=self.get_probability_for_stage(stage),
                expected_close_date=timezone.now().date() + timedelta(days=random.randint(10, 70)),
                actual_close_date=timezone.now().date() if stage in ['completed', 'closed_lost'] else None,
                next_step=self.get_next_step_for_stage(stage),
                lost_reason="Budget constraints" if stage == 'closed_lost' else "",
                notes="Direct opportunity from client inquiry",
            )
            opp.created_at = timezone.now() - timedelta(days=days_ago)
            opp.save(update_fields=['created_at'])

            opportunities.append(opp)

        return opportunities

    def get_probability_for_stage(self, stage):
        """Get probability percentage based on stage"""
        probabilities = {
            'qualified': 10,
            'proposal': 25,
            'shortlist': 40,
            'negotiation': 60,
            'contract_sent': 75,
            'po_received': 90,
            'in_execution': 95,
            'completed': 100,
            'closed_lost': 0,
        }
        return probabilities.get(stage, 10)

    def get_next_step_for_stage(self, stage):
        """Get next step description based on stage"""
        steps = {
            'qualified': "Schedule discovery call to understand requirements",
            'proposal': "Follow up on sent proposal, address questions",
            'shortlist': "Present final artist options and costs",
            'negotiation': "Finalize contract terms and artist fees",
            'contract_sent': "Awaiting signed contract and PO",
            'po_received': "Coordinate with artist and production team",
            'in_execution': "Monitor deliverable creation and approvals",
            'completed': "Invoice sent, collect final payment",
            'closed_lost': "",
        }
        return steps.get(stage, "")

    def create_proposals(self):
        """Create proposals for opportunities"""
        statuses = ['draft', 'sent', 'revised', 'accepted', 'rejected']

        proposals = []

        # Create proposals for opportunities that are past qualified stage
        eligible_opps = [opp for opp in self.opportunities if opp.stage not in ['qualified', 'closed_lost']]

        for opp in eligible_opps:
            # Some opportunities have multiple versions
            num_versions = random.randint(1, 3)

            for version in range(1, num_versions + 1):
                status = 'accepted' if version == num_versions and opp.stage in ['contract_sent', 'po_received', 'completed'] else random.choice(statuses)

                fee_gross = Decimal(random.randint(20000, 85000))
                discounts = Decimal(random.randint(0, 5000))
                agency_fee = Decimal(random.randint(2000, 8000))

                proposal = Proposal.objects.create(
                    opportunity=opp,
                    created_by=self.user,
                    version=version,
                    fee_gross=fee_gross,
                    discounts=discounts,
                    agency_fee=agency_fee,
                    fee_net=fee_gross - discounts - agency_fee,
                    currency='EUR',
                    proposal_status=status,
                    sent_date=timezone.now() - timedelta(days=random.randint(1, 30)) if status != 'draft' else None,
                    valid_until=timezone.now().date() + timedelta(days=30) if status in ['sent', 'revised'] else None,
                    notes=f"Proposal version {version} for {opp.opp_name}",
                )

                # Add artists to proposal
                num_artists = random.randint(1, 3)
                selected_artists = random.sample(self.artists, num_artists)

                for artist in selected_artists:
                    ProposalArtist.objects.create(
                        proposal=proposal,
                        artist=artist,
                        role=random.choice(['main', 'featured', 'guest']),
                        proposed_fee=Decimal(random.randint(10000, 30000)),
                    )

                proposals.append(proposal)

        return proposals

    def create_deals(self):
        """Create deals for won opportunities"""
        deal_statuses = ['draft', 'pending_signature', 'signed', 'active', 'completed']
        payment_terms = ['net_30', 'net_60', 'advance_50', 'advance_30', 'milestone']

        deals = []

        # Create deals for opportunities in late stages
        won_opps = [opp for opp in self.opportunities if opp.stage in ['contract_sent', 'po_received', 'in_execution', 'completed']]

        for opp in won_opps:
            # Get accepted proposal
            accepted_proposal = opp.proposals.filter(proposal_status='accepted').first()
            if not accepted_proposal:
                continue

            status = random.choice(deal_statuses)

            deal = Deal.objects.create(
                opportunity=opp,
                account=opp.account,
                deliverable_pack=random.choice(self.packs) if random.random() > 0.3 else None,
                usage_terms=random.choice(self.terms) if random.random() > 0.4 else None,
                department=self.department,
                created_by=self.user,
                po_number=f"PO-{random.randint(10000, 99999)}" if status not in ['draft'] else "",
                deal_title=opp.opp_name,
                start_date=timezone.now().date() + timedelta(days=random.randint(5, 30)),
                end_date=timezone.now().date() + timedelta(days=random.randint(90, 200)),
                signed_date=timezone.now().date() if status not in ['draft', 'pending_signature'] else None,
                fee_total=accepted_proposal.fee_net,
                currency='EUR',
                payment_terms=random.choice(payment_terms),
                deal_status=status,
                brand_safety_score=random.randint(7, 10),
                notes=f"Deal converted from opportunity {opp.opp_name}",
            )

            # Add artists from proposal
            for proposal_artist in accepted_proposal.proposal_artists.all():
                DealArtist.objects.create(
                    deal=deal,
                    artist=proposal_artist.artist,
                    role=proposal_artist.role,
                    artist_fee=proposal_artist.proposed_fee or Decimal(15000),
                    contract_status=random.choice(['pending', 'signed', 'active']),
                    signed_date=timezone.now().date() if status not in ['draft', 'pending_signature'] else None,
                )

            # Add deliverables based on pack or random
            if deal.deliverable_pack:
                for pack_item in deal.deliverable_pack.items.all():
                    DealDeliverable.objects.create(
                        deal=deal,
                        deliverable_type=pack_item.deliverable_type,
                        quantity=pack_item.quantity,
                        description=pack_item.description,
                        due_date=deal.start_date + timedelta(days=random.randint(14, 60)),
                        status=random.choice(['planned', 'in_progress', 'submitted', 'approved', 'completed']),
                    )
            else:
                # Random deliverables
                for _ in range(random.randint(2, 5)):
                    DealDeliverable.objects.create(
                        deal=deal,
                        deliverable_type=random.choice(['ig_post', 'ig_reel', 'tiktok_video', 'youtube_video', 'tvc']),
                        quantity=random.randint(1, 3),
                        description="Custom deliverable",
                        due_date=deal.start_date + timedelta(days=random.randint(14, 60)),
                        status=random.choice(['planned', 'in_progress', 'submitted', 'approved', 'completed']),
                    )

            deals.append(deal)

        return deals

    def create_approvals(self):
        """Create approval workflow items for deals"""
        approval_stages = ['concept', 'script', 'rough_cut', 'final_cut', 'caption', 'static_kv']
        approval_statuses = ['pending', 'approved', 'changes_requested', 'rejected']

        approvals = []

        for deal in self.deals:
            # Get some deliverables for this deal
            deliverables = list(deal.deliverables.all()[:3])

            for deliverable in deliverables:
                # Each deliverable might have 1-3 approval stages
                num_stages = random.randint(1, 3)

                for i in range(num_stages):
                    stage = random.choice(approval_stages)
                    status = random.choice(approval_statuses)

                    approval = Approval.objects.create(
                        deal=deal,
                        deliverable=deliverable,
                        stage=stage,
                        version=i + 1,
                        submitted_at=timezone.now() - timedelta(days=random.randint(1, 20)),
                        approved_at=timezone.now() - timedelta(days=random.randint(0, 10)) if status != 'pending' else None,
                        approver_contact=deal.account.contact_persons.first(),
                        status=status,
                        notes=self.get_approval_notes(status),
                    )

                    approvals.append(approval)

        return approvals

    def get_approval_notes(self, status):
        """Get sample approval notes based on status"""
        notes = {
            'pending': "Awaiting client review",
            'approved': "Looks great, approved to proceed",
            'changes_requested': "Please adjust brand logo size and change background color",
            'rejected': "Does not align with brand guidelines, please revise",
        }
        return notes.get(status, "")

    def print_summary(self):
        """Print summary of created data"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 SEED DATA SUMMARY'))
        self.stdout.write('='*60)

        self.stdout.write(f"\n🏢 Entities:")
        self.stdout.write(f"  • Brands: {len(self.brands)}")
        self.stdout.write(f"  • Agencies: {len(self.agencies)}")
        self.stdout.write(f"  • Artists: {len(self.artists)}")
        self.stdout.write(f"  • Contact Persons: {ContactPerson.objects.count()}")

        self.stdout.write(f"\n📦 Templates:")
        self.stdout.write(f"  • Deliverable Packs: {len(self.packs)}")
        self.stdout.write(f"  • Usage Terms: {len(self.terms)}")

        self.stdout.write(f"\n📋 Sales Pipeline:")
        self.stdout.write(f"  • Briefs: {len(self.briefs)}")
        for status in ['new', 'qualified', 'pitched', 'lost', 'won']:
            count = Brief.objects.filter(brief_status=status).count()
            self.stdout.write(f"    - {status}: {count}")

        self.stdout.write(f"\n  • Opportunities: {len(self.opportunities)}")
        for stage in ['qualified', 'proposal', 'shortlist', 'negotiation', 'contract_sent', 'completed', 'closed_lost']:
            count = Opportunity.objects.filter(stage=stage).count()
            if count > 0:
                self.stdout.write(f"    - {stage}: {count}")

        self.stdout.write(f"\n  • Proposals: {len(self.proposals)}")
        self.stdout.write(f"    - Total proposal artists: {ProposalArtist.objects.count()}")

        self.stdout.write(f"\n💼 Deals:")
        self.stdout.write(f"  • Total Deals: {len(self.deals)}")
        self.stdout.write(f"  • Deal Artists: {DealArtist.objects.count()}")
        self.stdout.write(f"  • Deal Deliverables: {DealDeliverable.objects.count()}")
        self.stdout.write(f"  • Approvals: {len(self.approvals)}")

        total_value = sum(deal.fee_total for deal in self.deals)
        self.stdout.write(f"\n💰 Total Deal Value: €{total_value:,.2f}")

        self.stdout.write('\n' + '='*60)
