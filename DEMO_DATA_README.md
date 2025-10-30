# Demo Data Setup for CRM System

This guide explains how to populate your local development database with demo data to visualize all the CRM features.

## ⚠️ IMPORTANT: LOCAL DEVELOPMENT ONLY

**This demo data is for LOCAL DEVELOPMENT ONLY**. Do not run this in production!

## What Gets Created

The demo data seeder will create:

### 👥 Users (5 Digital Department Team Members)
- Sarah Chen - Digital Manager
- Alex Morgan - PPC Specialist
- Maya Patel - Social Media Manager
- James Wilson - Content Creator
- Emma Davis - Analytics Lead

**Login credentials for all users:**
- Email: `[firstname.lastname]@hahahaproduction.com`
- Password: `demo123`

### 🏢 Entities
- **5 Clients**: Universal Music, Sony Music, Warner Music, Independent Records, Spotify Studios
- **5 Artists**: Taylor Swift, The Weeknd, Billie Eilish, Drake, Ariana Grande
- **5 Brands**: Nike, Apple Music, Red Bull, Coachella, YouTube Music

### 📊 Campaigns (6 Digital Campaigns)
1. **Taylor Swift - Eras Tour PPC Campaign** (Active)
   - Platform: Meta
   - Budget: €125,000 (67.5% spent)
   - KPIs: Impressions, Clicks, CTR, Conversions

2. **Billie Eilish - TikTok UGC Challenge** (Active)
   - Platform: TikTok
   - Budget: €85,000 (60% spent)
   - KPIs: Views, Engagement, Shares

3. **The Weeknd - Global DSP Distribution** (Active)
   - Platform: Spotify
   - Budget: €200,000 (66% spent)
   - KPIs: Streams, Monthly Listeners, Revenue

4. **Drake - Playlist Pitching Strategy** (Confirmed)
   - Platform: Spotify
   - Budget: €50,000
   - KPIs: Pitches, Acceptance Rate, Reach

5. **Ariana Grande - Radio Plugging EU Tour** (Negotiation)
   - Platform: Radio
   - Budget: €75,000
   - KPIs: Station Coverage, Weekly Plays

6. **Summer Festival PPC Campaign 2024** (Completed)
   - Platform: Google
   - Successfully exceeded KPIs by 110%

### ✅ Tasks (10 Tasks)
- Various priorities (Urgent, High, Normal, Low)
- Different statuses (To Do, In Progress, Blocked, Review, Done)
- Assigned to different team members
- With due dates, time tracking, and labels

### 📧 Activities (10 Communication Logs)
- Emails, phone calls, meetings, video calls
- With sentiment tracking (positive/neutral/negative)
- Follow-up requirements
- Linked to campaigns and entities

## How to Run

### Option 1: Django Management Command (Recommended)

```bash
cd backend

# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run the seeder
python manage.py seed_demo_data
```

### Option 2: Direct Script Execution

```bash
cd backend

# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run the script directly
python scripts/seed_demo_data.py
```

## After Seeding

1. **Start the backend server:**
   ```bash
   python manage.py runserver
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Login with a demo account:**
   - Email: `sarah.chen@hahahaproduction.com`
   - Password: `demo123`

4. **Navigate to the Digital Dashboard** to see:
   - Campaign overview with KPI tracking
   - Task management kanban board
   - Activity timeline
   - Client health scores
   - Financial metrics
   - Service performance analytics
   - AI insights and forecasting

## Features to Explore

### 📈 Digital Dashboard (`/digital-dashboard`)
- **Overview Tab**: See campaign performance cards and KPIs
- **Clients Tab**: View client health scores and revenue
- **Campaigns Tab**: Switch between Kanban and Table views
- **Services Tab**: Analyze service performance (PPC, TikTok, DSP)
- **Financial Tab**: Track budgets and invoices
- **Tasks Tab**: Manage tasks with different priorities
- **Reporting Tab**: View performance metrics and scheduled reports
- **Insights Tab**: See AI-powered insights and predictions

### ✅ Task Management (`/tasks`)
- View tasks in Kanban, List, or Calendar view
- Filter by priority, type, and assignee
- Track task progress and dependencies
- Create follow-up tasks

### 💬 Activity Timeline
- View all communication logs
- Filter by type and sentiment
- Create follow-up tasks from activities
- Track meeting notes and outcomes

## Troubleshooting

If you encounter any errors:

1. **Make sure migrations are up to date:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Check that required apps are installed:**
   - `entities`
   - `campaigns`
   - `crm_extensions`

3. **Verify your database is running:**
   - PostgreSQL should be running
   - Database connection configured in `.env`

4. **Clear existing data if needed:**
   ```bash
   python manage.py seed_demo_data --clear
   ```
   ⚠️ This will delete existing data!

## Data Relationships

```
Clients/Artists/Brands (Entities)
    ↓
Campaigns (with service type, platform, KPIs)
    ↓
Tasks (with priorities and assignments)
    ↓
Activities (communication logs with sentiment)
```

## Notes

- All financial values are in Euros (€)
- Dates are relative to the current date
- Some campaigns have historical metrics for the last 7 days
- Task dependencies are set up to show workflow relationships
- Activities include various sentiments to demonstrate the full range

## Customization

To modify the demo data, edit:
- `/backend/scripts/seed_demo_data.py`

You can adjust:
- Number of entities created
- Campaign values and KPIs
- Task priorities and assignments
- Activity types and sentiments