# Artist Sales - Seed Data Documentation

## Overview

Comprehensive seed data for testing and development of the Artist Sales CRM module.

## Command

```bash
# Seed data (preserves existing data)
python manage.py seed_artist_sales

# Clear existing artist sales data and re-seed
python manage.py seed_artist_sales --clear
```

## What Gets Created

### Entities (22 total)

**8 Brands:**
- Coca-Cola Romania (Beverage)
- Samsung Electronics (Technology)
- Nike Romania (Fashion)
- Vodafone Romania (Telecom)
- eMAG (E-commerce)
- Kaufland Romania (Retail)
- Heineken Romania (Beverage)
- Decathlon Romania (Sports)

**4 Agencies:**
- Publicis Romania (Publicis Groupe)
- McCann Bucharest (McCann Worldgroup)
- Leo Burnett Romania (Publicis Groupe)
- Ogilvy Romania (WPP)

**10 Artists (with A/B/C tier ratings):**
- Smiley (A-Tier)
- INNA (A-Tier)
- Carla's Dreams (A-Tier)
- The Motans (B-Tier)
- Irina Rimes (B-Tier)
- Connect-R (B-Tier)
- Delia (B-Tier)
- Antonia (C-Tier)
- Corina (C-Tier)
- Nicole Cherry (C-Tier)

### Contact Persons (69 total)

1-2 contact persons per brand/agency with realistic:
- Names (Romanian names)
- Roles (marketing, brand, pr, a&r)
- Engagement stages (active, prospect, partner)
- Sentiment (supportive, professional, friendly)

### Deliverable Packs (5 templates)

1. **Standard Social Media Package**
   - 2x Instagram Post
   - 3x Instagram Story
   - 1x Instagram Reel

2. **TikTok Campaign Bundle**
   - 4x TikTok Video
   - 2x Instagram Reel

3. **YouTube Integration**
   - 1x YouTube Video
   - 3x YouTube Short

4. **ATL Campaign (TV + Digital)**
   - 1x TV Commercial
   - 5x Digital Banner
   - 2x Instagram Post

5. **Event Appearance**
   - 1x Event Appearance
   - 5x Instagram Story
   - 2x Instagram Post

### Usage Terms (7 templates)

1. Digital Only - 12 months (Romania)
2. Social Media - 6 months (CEE: RO, BG, HU, CZ, PL)
3. ATL + BTL - 24 months with Beverage exclusivity
4. Global Rights - Perpetual Buyout
5. OOH + Packaging - 18 months
6. Broadcast (TV + Radio) - 12 months with Automotive exclusivity
7. Digital + In-Store - 6 months

### Sales Pipeline

**10 Briefs** across various statuses:
- New (3)
- Qualified (1)
- Pitched (3)
- Lost (3)
- Won (0)

**15 Opportunities** across pipeline stages:
- Qualified (2)
- Proposal (1)
- Shortlist (2)
- Negotiation (1)
- Contract Sent (1)
- Completed (2)
- Closed Lost (3)

**19 Proposals** with:
- Multiple versions (up to 3 versions per opportunity)
- Versioning (v1, v2, v3)
- Various statuses (draft, sent, revised, accepted, rejected)
- Realistic pricing (€20,000 - €85,000 range)

**37 ProposalArtists**:
- Artists assigned to proposals
- Roles (main, featured, guest)
- Proposed fees

### Active Deals

**6 Deals** (Total value: ~€160,000)
- Contract numbers (auto-generated)
- PO numbers
- Linked to won opportunities
- Various statuses (draft, pending_signature, signed, active, completed)
- Payment terms (net_30, net_60, advance_50, etc.)
- Start/end dates
- Brand safety scores (7-10)

**12 DealArtists**:
- Artists assigned to deals
- Individual artist fees
- Contract status (pending, signed, active)

**15 DealDeliverables**:
- Based on deliverable packs or custom
- Various types (IG Post, Reel, TikTok, TVC, etc.)
- Statuses: planned, in_progress, submitted, approved, completed
- Due dates

**28 Approvals**:
- Multi-stage approval workflow
- Stages: concept, script, rough_cut, final_cut, caption, static_kv
- Statuses: pending, approved, changes_requested, rejected
- Versioning
- Approval notes

## Data Relationships

The seed data creates a realistic flow:

```
Brief (10)
  ↓ (8 converted)
Opportunity (15)
  ↓ (10 with proposals)
Proposal (19) + ProposalArtists (37)
  ↓ (6 converted to deals)
Deal (6) + DealArtists (12) + DealDeliverables (15)
  ↓
Approvals (28)
```

## Realistic Features

- **Dates**: Spread across realistic timelines (past 60 days for briefs, future dates for deliveries)
- **Amounts**: Realistic pricing for Romanian market (€5,000 - €100,000 range)
- **Statuses**: Distributed across various pipeline stages
- **Versioning**: Proposals have multiple versions showing iteration
- **Contact Context**: Each brand/agency has proper contact persons
- **Artist Tiers**: Artists properly categorized as A/B/C tier
- **Multi-artist deals**: Deals can have multiple artists (main, featured, guest)
- **Approval workflow**: Realistic multi-stage approval process

## Use Cases

### Testing Brief → Deal Flow
1. View briefs in various statuses
2. See conversion to opportunities
3. Track proposal versions
4. Monitor deal progression

### Testing Artist Management
- View artists by tier
- See artist assignments in proposals
- Track artist fees in deals

### Testing Deliverables & Approvals
- Monitor deliverable status
- Track approval workflows
- View pending/approved items

### Testing Templates
- Use deliverable packs in new deals
- Apply usage terms templates
- Reuse pack configurations

## Clearing Data

The `--clear` flag will delete ALL artist sales data:
- Approvals
- DealDeliverables
- DealArtists
- Deals
- ProposalArtists
- Proposals
- Opportunities
- Briefs
- DeliverablePackItems
- DeliverablePacks
- UsageTerms

**Warning**: This does NOT delete Entities (brands, agencies, artists) or ContactPersons, as they may be used by other modules.

## Development Tips

1. **Fresh Start**: Use `--clear` when you want completely fresh data
2. **Incremental**: Run without `--clear` to add more data
3. **Testing**: Great for testing list views, filters, and stats endpoints
4. **Demos**: Use for client demos with realistic Romanian artist names
5. **Edge Cases**: Includes various statuses and edge cases (lost deals, rejected proposals, etc.)

## Example Queries

```python
# Get all A-tier artists
Entity.objects.filter(rate_tier='A', entity_roles__role='artist')

# Get active deals with artists
Deal.objects.filter(deal_status='active').prefetch_related('deal_artists')

# Get pending approvals
Approval.objects.filter(status='pending')

# Get opportunities by stage
Opportunity.objects.filter(stage='negotiation')

# Get proposals by status
Proposal.objects.filter(proposal_status='sent')
```

## Stats Available

After seeding, you can test:
- Brief stats endpoint (`/api/v1/artist-sales/briefs/stats/`)
- Opportunity pipeline (`/api/v1/artist-sales/opportunities/pipeline/`)
- Proposal stats (`/api/v1/artist-sales/proposals/stats/`)
- Deal stats (`/api/v1/artist-sales/deals/stats/`)

All endpoints will return realistic data based on the seeded records.
