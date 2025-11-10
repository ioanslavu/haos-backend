"""
Django management command to populate sample opportunities data for development.

Usage:
    python manage.py populate_sample_opportunities

WARNING: This is for DEVELOPMENT ONLY. Do not run on production!
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from decimal import Decimal
from identity.models import Entity
from api.models import Department
from artist_sales.models import (
    Opportunity, OpportunityTask, OpportunityActivity,
    OpportunityArtist, OpportunityComment
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate sample opportunities data for development (DO NOT USE IN PRODUCTION)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing opportunities before populating',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  WARNING: This command is for DEVELOPMENT ONLY!'))
        self.stdout.write('')

        # Safety check - don't run if we have too many opportunities (likely prod)
        existing_count = Opportunity.objects.count()
        if existing_count > 50:
            self.stdout.write(self.style.ERROR(
                f'❌ Safety check failed: Found {existing_count} opportunities. '
                'This command should only run on development environments with minimal data.'
            ))
            return

        if options['clear']:
            self.stdout.write('🗑️  Clearing existing opportunities...')
            Opportunity.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing opportunities'))

        # Get or create test users and entities
        self.stdout.write('👤 Getting users and entities...')
        users = list(User.objects.filter(is_active=True)[:5])
        if not users:
            self.stdout.write(self.style.ERROR('❌ No active users found. Please create users first.'))
            return

        # Brands are Legal Entities (PJ)
        brands = list(Entity.objects.filter(kind='PJ')[:10])
        if not brands:
            self.stdout.write(self.style.WARNING('⚠️  No brands (legal entities) found. Creating sample brands...'))
            brands = self._create_sample_brands()

        # Artists are Physical Persons (PF)
        artists = list(Entity.objects.filter(kind='PF')[:10])
        if not artists:
            self.stdout.write(self.style.WARNING('⚠️  No artists (physical persons) found. Creating sample artists...'))
            artists = self._create_sample_artists()

        departments = list(Department.objects.all()[:3])

        self.stdout.write(self.style.SUCCESS(f'✓ Found {len(users)} users, {len(brands)} brands, {len(artists)} artists'))

        # Create sample opportunities
        self.stdout.write('')
        self.stdout.write('🎯 Creating sample opportunities...')

        opportunities_data = [
            {
                'title': 'Nike Summer Campaign 2025',
                'stage': 'proposal_sent',
                'priority': 'high',
                'estimated_value': '150000.00',
                'campaign_objectives': 'Launch new athletic wear line targeting Gen Z athletes',
                'target_audience': 'Athletes aged 18-25, focus on basketball and running',
                'brand_category': 'Sports & Athletics',
                'channels': ['instagram', 'tiktok', 'youtube'],
                'expected_close_date': timezone.now() + timedelta(days=30),
            },
            {
                'title': 'Adidas x Urban Culture Collab',
                'stage': 'negotiation',
                'priority': 'urgent',
                'estimated_value': '200000.00',
                'campaign_objectives': 'Street culture collaboration with 3 major influencers',
                'target_audience': 'Urban youth 16-28, streetwear enthusiasts',
                'brand_category': 'Fashion & Lifestyle',
                'channels': ['instagram', 'tiktok'],
                'expected_close_date': timezone.now() + timedelta(days=15),
            },
            {
                'title': 'Coca-Cola Music Festival Activation',
                'stage': 'brief',
                'priority': 'medium',
                'estimated_value': '80000.00',
                'campaign_objectives': 'Festival season brand presence with artist performances',
                'target_audience': 'Festival goers 18-35',
                'brand_category': 'Beverages',
                'channels': ['instagram', 'youtube', 'tiktok'],
                'budget_range_min': '70000.00',
                'budget_range_max': '90000.00',
            },
            {
                'title': 'BMW Electric Vehicle Launch',
                'stage': 'qualified',
                'priority': 'high',
                'estimated_value': '300000.00',
                'campaign_objectives': 'Launch campaign for new EV model with tech influencers',
                'target_audience': 'Tech-savvy professionals 25-45, eco-conscious consumers',
                'brand_category': 'Automotive',
                'channels': ['youtube', 'instagram'],
                'expected_close_date': timezone.now() + timedelta(days=60),
            },
            {
                'title': 'Samsung Galaxy Content Series',
                'stage': 'shortlist',
                'priority': 'medium',
                'estimated_value': '120000.00',
                'campaign_objectives': 'Monthly content series showcasing phone camera capabilities',
                'target_audience': 'Photography enthusiasts, content creators 20-40',
                'brand_category': 'Technology',
                'channels': ['instagram', 'youtube'],
            },
            {
                'title': 'Sephora Beauty Ambassador Program',
                'stage': 'won',
                'priority': 'high',
                'estimated_value': '180000.00',
                'campaign_objectives': 'Annual beauty ambassador program with 5 influencers',
                'target_audience': 'Beauty enthusiasts 18-35, primarily female',
                'brand_category': 'Beauty & Cosmetics',
                'channels': ['instagram', 'tiktok', 'youtube'],
                'expected_close_date': timezone.now() - timedelta(days=5),
                'contract_number': 'AS-2025-00001',
            },
            {
                'title': 'Red Bull Extreme Sports Series',
                'stage': 'executing',
                'priority': 'urgent',
                'estimated_value': '250000.00',
                'campaign_objectives': 'Year-long extreme sports content with athlete influencers',
                'target_audience': 'Extreme sports fans 16-30',
                'brand_category': 'Energy Drinks & Sports',
                'channels': ['youtube', 'instagram', 'tiktok'],
                'contract_number': 'AS-2025-00002',
            },
            {
                'title': 'L\'Oréal Hair Care Campaign',
                'stage': 'proposal_draft',
                'priority': 'medium',
                'estimated_value': '95000.00',
                'campaign_objectives': 'New hair care product line launch with beauty creators',
                'target_audience': 'Women 25-45 interested in hair care',
                'brand_category': 'Beauty & Personal Care',
                'channels': ['instagram', 'tiktok'],
            },
            {
                'title': 'PlayStation Gaming Tournament',
                'stage': 'contract_prep',
                'priority': 'high',
                'estimated_value': '175000.00',
                'campaign_objectives': 'E-sports tournament sponsorship and streaming content',
                'target_audience': 'Gamers 16-30, competitive gaming community',
                'brand_category': 'Gaming',
                'channels': ['twitch', 'youtube'],
                'expected_close_date': timezone.now() + timedelta(days=20),
            },
            {
                'title': 'Spotify Podcast Series',
                'stage': 'closed_lost',
                'priority': 'low',
                'estimated_value': '60000.00',
                'campaign_objectives': 'Original podcast series with music influencers',
                'target_audience': 'Music lovers 20-40, podcast listeners',
                'brand_category': 'Music & Entertainment',
                'channels': ['podcast', 'instagram'],
                'lost_reason': 'Budget constraints from client',
            },
        ]

        created_opportunities = []
        for i, opp_data in enumerate(opportunities_data):
            # Assign random user as owner
            owner = users[i % len(users)]
            account = brands[i % len(brands)]

            opportunity = Opportunity.objects.create(
                account=account,
                owner=owner,
                team=departments[0] if departments else None,
                currency='EUR',
                **opp_data
            )
            created_opportunities.append(opportunity)

            # Add some artists to opportunities
            if i % 2 == 0 and artists:  # Every other opportunity gets artists
                artist_entity = artists[i % len(artists)]
                OpportunityArtist.objects.create(
                    opportunity=opportunity,
                    artist=artist_entity,
                    role='primary',
                    proposed_fee='15000.00',
                    confirmed_fee='14000.00' if opportunity.stage in ['won', 'executing'] else None,
                    contract_status='signed' if opportunity.stage == 'won' else 'pending',
                )

            # Add tasks to active opportunities
            if opportunity.stage in ['proposal_sent', 'negotiation', 'won', 'executing']:
                OpportunityTask.objects.create(
                    opportunity=opportunity,
                    title='Follow up with client',
                    task_type='follow_up',
                    priority='high' if opportunity.priority == 'urgent' else 'medium',
                    status='in_progress' if opportunity.stage != 'won' else 'completed',
                    assigned_to=owner,
                    due_date=timezone.now() + timedelta(days=3),
                )

            # Add activity
            OpportunityActivity.objects.create(
                opportunity=opportunity,
                activity_type='stage_change',
                user=owner,
                description=f'Created opportunity in {opportunity.get_stage_display()} stage',
            )

            self.stdout.write(f'  ✓ Created: {opportunity.title} [{opportunity.get_stage_display()}]')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully created {len(created_opportunities)} sample opportunities!'))
        self.stdout.write('')
        self.stdout.write('📊 Breakdown by stage:')

        stages = Opportunity.objects.values('stage').annotate(count=Count('id')).order_by('stage')
        for stage_data in stages:
            stage_label = dict(Opportunity.STAGE_CHOICES).get(stage_data['stage'], stage_data['stage'])
            self.stdout.write(f"  • {stage_label}: {stage_data['count']}")

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Done! Visit http://localhost:5173/opportunities to view the opportunities.'))

    def _create_sample_brands(self):
        """Create sample brand entities (Legal Entities)"""
        brand_names = [
            'Nike Inc.', 'Adidas Group', 'Coca-Cola Company', 'BMW AG',
            'Samsung Electronics', 'Sephora', 'Red Bull GmbH', 'L\'Oréal',
            'Sony PlayStation', 'Spotify AB'
        ]

        brands = []
        for name in brand_names:
            brand = Entity.objects.create(
                kind='PJ',  # Legal Entity
                display_name=name,
            )
            brands.append(brand)

        return brands

    def _create_sample_artists(self):
        """Create sample artist entities (Physical Persons)"""
        artist_names = [
            'Alex Turner', 'Maya Chen', 'Jordan Lee', 'Sofia Rodriguez',
            'Marcus Johnson', 'Emma Wilson', 'Kai Nakamura', 'Luna Santos',
            'Noah Kim', 'Aria Patel'
        ]

        artists = []
        for name in artist_names:
            first_name, last_name = name.split()
            artist = Entity.objects.create(
                kind='PF',  # Physical Person
                display_name=name,
                first_name=first_name,
                last_name=last_name,
            )
            artists.append(artist)

        return artists
