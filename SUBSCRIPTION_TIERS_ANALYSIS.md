# WhoVoted Subscription Tiers - Implementation Plan

## User-Provided Specification

The following subscription tiers have been defined with specific pricing, data scope, capabilities, and restrictions:

### TIER 1: Individual / Power User
**Purpose**: Non-affiliated individuals (super voters, activists, researchers, journalists) who want to explore election data, but do not run campaigns.

**Pricing**:
- Monthly: $50
- 3-month: $135
- 6-month: $240
- Annual: $390

**Data Scope**:
- Geography: Broader map (county or region), no "owned" campaigns or territories
- Time window: Last 5 years of elections in selected geography
- Data types: Voter registration fields, vote history flags, basic demographics, party, precinct/district tags, precinct-level results and turnout

**Capabilities (Allowed)**:
- Read-only dashboards and maps
- Filter and explore data on screen (by election, precinct, district, party, turnout bands, etc.)
- View simple trend charts: turnout over time, partisan balance over time, top-changing precincts
- Optional: Limited number of saved "views" or bookmarks (teaser for upsell)

**Restrictions (NOT Allowed)**:
- No campaign creation or campaign objects
- No turf cutting or list-building tools
- No exports (CSV/Excel/PDF) of voter lists
- No integrations (no sync to dialers, SMS tools, CRMs, etc.)
- No volunteer, donor, or contact-tracking tools

---

### TIER 2: Candidate
**Purpose**: A candidate running in a single race who needs a focused view of their turf and recent history, but not full operational tools.

**Pricing**:
- Monthly: $200
- 3-month: $540
- 6-month: $960
- Annual: $1,560

**Data Scope**:
- Geography: One chosen territory (their district/county/defined turf)
- Time window: Current election plus last 4 elections in that territory
- Data types: Same as Individual, but scoped to candidate's territory; includes turnout and results per precinct for those 4 elections

**Capabilities (Allowed)**:
- Read-only dashboards for "my race": Registered voters, turnout trends, vote share trends
- Precinct-level maps for the current and prior 4 elections
- Filter and explore within their territory (election, precinct, party, turnout bands, etc.)
- Save race-centric views (e.g., "base precincts", "swing precincts") as on-screen bookmarks

**Restrictions (NOT Allowed)**:
- No list-building or turf cutting tools
- No walk sheet generation (print or digital)
- No phone/SMS/email export lists
- No detailed or custom reporting (only the standard dashboards)
- No integrations with external tools
- Limited number of users (candidate + 1–2 helpers; configurable)

---

### TIER 3: Campaign Manager
**Purpose**: Person responsible for running operations for a single campaign in a defined territory; needs full field and reporting tools, but only for that one campaign.

**Pricing**:
- Monthly: $250
- 3-month: $675
- 6-month: $1,200
- Annual: $1,950

**Data Scope**:
- Geography: One chosen territory (same model as candidate)
- Time window: Full historical data for that territory (not capped at 4 elections)
- Data types: Full voter file, vote history, demographics, party, precinct/district tags, past results, plus any donor/volunteer/event data supported

**Capabilities (Allowed)**:
- All read-only capabilities of Candidate, PLUS:
- Campaign object for that territory (one managed campaign)
- Full list-building tools (filtering, segmentation, saved lists)
- Turf cutting and assignment tools (define turf, assign to canvassers)
- Walk list generation (print and digital/app)
- Phone/SMS/email export lists, including format presets for common dialers/SMS tools
- Volunteer and contact tracking (contacts, canvass results, responses)
- Basic fundraising/comms modules (donor segments, event tracking, simple pipelines)
- Full reporting dashboards for that territory: Doors knocked, contacts made, support levels, turnout and performance by precinct, activity by staff/volunteers
- Multi-user support (campaign team members with roles/permissions) within that one campaign

**Restrictions (NOT Allowed)**:
- No multi-campaign management (only one active campaign/territory per account)
- No cross-campaign analytics
- No client/agency-style folders

---

### TIER 4: Consultant (Multi-Campaign)
**Purpose**: Consultants, politiqueras, or firms managing multiple campaigns and geographies; needs all tools plus multi-campaign analytics and client separation.

**Pricing**:
- Monthly: $450
- 3-month: $1,215
- 6-month: $2,160
- Annual: $3,510

**Data Scope**:
- Geography: Multiple territories and campaigns (configurable maximums per subscription)
- Time window: Full historical data available across all configured territories
- Data types: Same as Campaign Manager, but across many campaigns/territories

**Capabilities (Allowed)**:
- All capabilities of Campaign Manager, for multiple campaigns, PLUS:
- Create and manage multiple campaign workspaces
- Assign team members per campaign (role-based access)
- Cross-campaign dashboards and reports (e.g., overall door knocks, contacts, and performance across all managed campaigns)
- Client folders or labels to group campaigns by client
- Optional white-label elements (logo, naming) if supported
- High-level "portfolio view" of performance by race, by geography, by staff

**Restrictions (NOT Allowed)**:
- Any hard caps decided (e.g., maximum campaigns, maximum territories, seats) can be enforced here, but conceptually no functional restrictions compared to Campaign Manager; this role is the superset

---

## Current Platform Capabilities (What We Have Built)

### Data & Analytics
- ✅ Interactive voter map with geocoded locations
- ✅ District boundaries (Congressional, State House, Commissioner)
- ✅ District report cards with demographics, party breakdown, age groups
- ✅ Historical voting data (multiple elections)
- ✅ Real-time data scraping from election officials
- ✅ AI-powered natural language query system (LLM integration)

### Campaign Tools
- ✅ Precinct performance reports (turnout rankings)
- ✅ Party switchers identification (R→D, D→R)
- ✅ New voter identification (first-time primary voters)
- ✅ Turf cuts / Non-voter lists (with geocoded addresses for mapping)
- ✅ Walk list generation capability (optimized routes)
- ✅ Export functionality (CSV, print-ready formats)

### Admin Features
- ✅ Data upload/import system
- ✅ Admin dashboard
- ✅ User authentication (basic)
- ⚠️ Multi-user/role management (needs enhancement)
- ⚠️ Campaign workspace isolation (needs implementation)

### Missing Features (Need to Build)
- ❌ Subscription/billing system
- ❌ Role-based access control (RBAC)
- ❌ Campaign object/workspace management
- ❌ Volunteer/contact tracking
- ❌ Fundraising/donor modules
- ❌ Integration APIs (dialers, SMS, CRM)
- ❌ Usage limits enforcement
- ❌ White-label capabilities

---

## Tier Mapping to Current Features

### TIER 1: Individual / Power User ($50/mo, $390/yr)

**What They Get (Current Features)**:
- ✅ Read-only access to voter map
- ✅ View district report cards (all districts in selected geography)
- ✅ Filter by election, precinct, district, party, turnout
- ✅ View trend charts (turnout over time, partisan shifts)
- ✅ AI query system (read-only, limited queries per month)
- ✅ Saved bookmarks/views (browser-based or simple DB storage)

**Restrictions to Enforce**:
- 🔒 No access to Campaign Reports module (`/reports.html`)
- 🔒 No export buttons (hide CSV/PDF download)
- 🔒 No turf cutting tools
- 🔒 No walk list generation
- 🔒 Geography limit: County or region (not single precinct)
- 🔒 Time window: Last 5 years only
- 🔒 AI query limit: 50 queries/month

**Technical Implementation**:
```python
# User model addition
role = 'INDIVIDUAL'
max_territories = 0  # No owned campaigns
history_years = 5
can_export = False
can_create_campaign = False
ai_query_limit = 50
```

**Recommendation**: This tier is perfect for our current "public gazette" view. Just add authentication and hide the campaign tools.

---

### TIER 2: Candidate ($200/mo, $1,560/yr)

**What They Get (Current Features)**:
- ✅ All Individual features, PLUS:
- ✅ Focus on ONE territory (their district)
- ✅ District report card for their race
- ✅ Precinct-level maps for current + last 4 elections
- ✅ Precinct performance report (read-only)
- ✅ Party switchers report (read-only, no export)
- ✅ New voters report (read-only, no export)
- ✅ AI query system (unlimited within their territory)
- ✅ Save race-centric views ("base precincts", "swing precincts")

**Restrictions to Enforce**:
- 🔒 No list building (can VIEW reports but not export lists)
- 🔒 No turf cutting
- 🔒 No walk sheets
- 🔒 No phone/SMS/email exports
- 🔒 Limited users: Candidate + 2 helpers (3 total)
- 🔒 One territory only
- 🔒 Time window: Current + last 4 elections

**Technical Implementation**:
```python
role = 'CANDIDATE'
max_territories = 1
territory_id = 'TX-15'  # Their district
history_elections = 4
can_view_reports = True
can_export = False
can_build_lists = False
max_users = 3
ai_query_limit = -1  # Unlimited
```

**Recommendation**: This is a "view-only campaign intelligence" tier. They see the insights but can't operationalize them. Good upsell path to Campaign Manager.

---

### TIER 3: Campaign Manager ($250/mo, $1,950/yr)

**What They Get (Current Features)**:
- ✅ All Candidate features, PLUS:
- ✅ Full access to Campaign Reports module
- ✅ List building: Filter and save voter segments
- ✅ Turf cutting: Define turfs, assign to canvassers
- ✅ Walk list generation (print and digital)
- ✅ Export lists: CSV for phone/SMS/email (with dialer presets)
- ✅ Contact tracking: Log canvass results, responses
- ✅ Full historical data (not limited to 4 elections)
- ✅ Multi-user support with roles (Campaign Manager, Canvasser, Volunteer)

**New Features Needed**:
- ❌ Campaign workspace object (isolate data per campaign)
- ❌ Volunteer management module
- ❌ Contact/canvass result tracking
- ❌ Basic fundraising module (donor segments, event tracking)
- ❌ Activity dashboards (doors knocked, contacts made)

**Technical Implementation**:
```python
role = 'CAMPAIGN_MANAGER'
max_territories = 1
max_campaigns = 1
campaign_id = 'camp_tx15_2026'
history_years = -1  # Full history
can_create_campaign = True
can_build_lists = True
can_cut_turf = True
can_export_data = True
can_manage_volunteers = True
can_track_fundraising = True
has_advanced_reporting = True
max_users = 15  # Campaign team
```

**Recommendation**: This is our "full-featured single campaign" tier. Most of the tools exist, but we need to add:
1. Campaign workspace isolation
2. Volunteer/contact tracking module
3. Role-based permissions within campaign

---

### TIER 4: Consultant / Multi-Campaign ($450/mo, $3,510/yr)

**What They Get (Current Features)**:
- ✅ All Campaign Manager features, PLUS:
- ✅ Multiple campaign workspaces
- ✅ Cross-campaign analytics dashboard
- ✅ Client folders/labels
- ✅ Portfolio view (performance across all campaigns)
- ✅ Team member assignment per campaign

**New Features Needed**:
- ❌ Multi-campaign management UI
- ❌ Cross-campaign reporting dashboard
- ❌ Client/folder organization
- ❌ White-label options (logo, branding)
- ❌ Agency-level user management

**Technical Implementation**:
```python
role = 'CONSULTANT'
max_territories = -1  # Unlimited
max_campaigns = 10  # Or unlimited with higher tier
history_years = -1
can_manage_multiple_campaigns = True
has_cross_campaign_reporting = True
can_white_label = True
max_users = 50  # Across all campaigns
```

**Recommendation**: This is the "agency/consultant" tier. Requires significant new development:
1. Multi-campaign workspace architecture
2. Cross-campaign analytics
3. Client management system
4. White-label capabilities

---

## Feature-to-Tier Mapping Matrix

| Feature | Individual | Candidate | Campaign Mgr | Consultant |
|---------|-----------|-----------|--------------|------------|
| **Data Access** |
| Voter map (read-only) | ✅ | ✅ | ✅ | ✅ |
| District report cards | ✅ | ✅ | ✅ | ✅ |
| Historical data | 5 years | 4 elections | Full | Full |
| Geography scope | County/Region | 1 District | 1 District | Multiple |
| **Analytics** |
| Trend charts | ✅ | ✅ | ✅ | ✅ |
| AI queries | 50/month | Unlimited | Unlimited | Unlimited |
| Precinct performance | View only | View only | Full access | Full access |
| Party switchers | View only | View only | Full access | Full access |
| New voters | View only | View only | Full access | Full access |
| **Campaign Tools** |
| Campaign workspace | ❌ | ❌ | 1 campaign | Multiple |
| List building | ❌ | ❌ | ✅ | ✅ |
| Turf cutting | ❌ | ❌ | ✅ | ✅ |
| Walk lists | ❌ | ❌ | ✅ | ✅ |
| Export (CSV/PDF) | ❌ | ❌ | ✅ | ✅ |
| **Team Management** |
| Users | 1 | 3 | 15 | 50+ |
| Volunteer tracking | ❌ | ❌ | ✅ | ✅ |
| Contact tracking | ❌ | ❌ | ✅ | ✅ |
| Fundraising module | ❌ | ❌ | ✅ | ✅ |
| **Advanced** |
| Multi-campaign | ❌ | ❌ | ❌ | ✅ |
| Cross-campaign analytics | ❌ | ❌ | ❌ | ✅ |
| White-label | ❌ | ❌ | ❌ | ✅ |

---

## Database Schema Recommendations

### New Tables Needed

```sql
-- Subscription plans
CREATE TABLE subscription_plans (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,  -- 'INDIVIDUAL', 'CANDIDATE', 'CAMPAIGN_MANAGER', 'CONSULTANT'
    display_name TEXT,
    price_monthly REAL,
    price_3_month REAL,
    price_6_month REAL,
    price_annual REAL,
    max_territories INTEGER,  -- -1 for unlimited
    max_campaigns INTEGER,
    history_years INTEGER,  -- -1 for full
    history_elections INTEGER,  -- -1 for full
    can_create_campaign BOOLEAN,
    can_manage_multiple_campaigns BOOLEAN,
    can_build_lists BOOLEAN,
    can_cut_turf BOOLEAN,
    can_export_data BOOLEAN,
    can_manage_volunteers BOOLEAN,
    can_track_fundraising BOOLEAN,
    has_advanced_reporting BOOLEAN,
    has_cross_campaign_reporting BOOLEAN,
    can_white_label BOOLEAN,
    ai_query_limit INTEGER,  -- -1 for unlimited
    max_users INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- User accounts (enhance existing)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    organization TEXT,
    subscription_plan_id INTEGER REFERENCES subscription_plans(id),
    subscription_status TEXT,  -- 'active', 'trial', 'expired', 'cancelled'
    subscription_start DATE,
    subscription_end DATE,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    ai_queries_used INTEGER DEFAULT 0,
    ai_queries_reset_date DATE,
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans(id)
);

-- Campaigns (new)
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY,
    owner_user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    territory_type TEXT,  -- 'congressional', 'state_house', 'commissioner', 'county'
    territory_id TEXT,  -- 'TX-15', 'HD-39', 'Hidalgo'
    election_date DATE,
    status TEXT,  -- 'active', 'archived', 'completed'
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

-- Campaign team members
CREATE TABLE campaign_users (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT,  -- 'manager', 'staff', 'volunteer', 'viewer'
    permissions TEXT,  -- JSON of specific permissions
    added_at TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(campaign_id, user_id)
);

-- Saved lists (for list building)
CREATE TABLE saved_lists (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    filters TEXT,  -- JSON of filter criteria
    voter_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Turf assignments
CREATE TABLE turfs (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    assigned_user_id INTEGER,
    precinct_list TEXT,  -- JSON array of precincts
    voter_count INTEGER,
    geometry TEXT,  -- GeoJSON polygon
    created_at TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id)
);

-- Contact tracking
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    voter_vuid TEXT NOT NULL,
    contacted_by_user_id INTEGER,
    contact_date TIMESTAMP,
    contact_type TEXT,  -- 'door', 'phone', 'text', 'email'
    response TEXT,  -- 'support', 'oppose', 'undecided', 'not_home', 'refused'
    notes TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (contacted_by_user_id) REFERENCES users(id)
);

-- Usage tracking (for limits)
CREATE TABLE usage_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    action_type TEXT,  -- 'ai_query', 'export', 'list_build', 'walk_list'
    resource_id TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## Implementation Priority

### Phase 1: Core Subscription System (Week 1-2)
1. ✅ Create subscription_plans table with 4 tiers
2. ✅ Enhance users table with subscription fields
3. ✅ Add authentication middleware with role checking
4. ✅ Implement feature flags based on subscription tier
5. ✅ Add Stripe integration for billing
6. ✅ Create subscription management UI

### Phase 2: Campaign Workspaces (Week 3-4)
1. ✅ Create campaigns table
2. ✅ Add campaign creation UI
3. ✅ Implement data isolation per campaign
4. ✅ Add campaign_users for team management
5. ✅ Update all reports to filter by campaign_id

### Phase 3: List Building & Turf Cutting (Week 5-6)
1. ✅ Create saved_lists table
2. ✅ Build list builder UI with filters
3. ✅ Create turfs table
4. ✅ Build turf cutting UI
5. ✅ Add export functionality with format presets

### Phase 4: Contact & Volunteer Tracking (Week 7-8)
1. ✅ Create contacts table
2. ✅ Build contact logging UI
3. ✅ Add volunteer management
4. ✅ Create activity dashboards

### Phase 5: Multi-Campaign & Consultant Features (Week 9-10)
1. ✅ Multi-campaign workspace switcher
2. ✅ Cross-campaign analytics dashboard
3. ✅ Client folders/labels
4. ✅ White-label options

---

## Pricing Analysis

Your pricing is competitive and well-structured:

| Tier | Monthly | Annual | Annual Savings | $/month (annual) |
|------|---------|--------|----------------|------------------|
| Individual | $50 | $390 | 22% | $32.50 |
| Candidate | $200 | $1,560 | 22% | $130 |
| Campaign Mgr | $250 | $1,950 | 22% | $162.50 |
| Consultant | $450 | $3,510 | 22% | $292.50 |

**Recommendations**:
1. ✅ Pricing is appropriate for the value provided
2. ✅ Clear upgrade path (Individual → Candidate → Manager → Consultant)
3. ✅ Annual discount (22%) incentivizes commitment
4. 💡 Consider adding a FREE tier (view-only, 1 district, no AI) for lead generation
5. 💡 Consider usage-based pricing for Consultant (per campaign or per user)

---

## Technical Recommendations

### 1. Middleware for Access Control
```python
# backend/auth.py
def require_subscription(min_tier='INDIVIDUAL'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or not user.has_active_subscription():
                return jsonify({'error': 'Subscription required'}), 403
            if not user.has_tier(min_tier):
                return jsonify({'error': 'Upgrade required'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_feature(feature_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user.can_access_feature(feature_name):
                return jsonify({'error': f'Feature not available in your plan'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage:
@app.route('/api/export-list', methods=['POST'])
@require_feature('can_export_data')
def export_list():
    # Export logic
    pass
```

### 2. Frontend Feature Flags
```javascript
// public/auth.js
const userPlan = {
    tier: 'CAMPAIGN_MANAGER',
    features: {
        can_export: true,
        can_build_lists: true,
        can_cut_turf: true,
        // ... from subscription_plans table
    }
};

function canAccess(feature) {
    return userPlan.features[feature] === true;
}

// Usage:
if (canAccess('can_export')) {
    showExportButton();
} else {
    showUpgradePrompt('Export feature requires Campaign Manager plan');
}
```

### 3. Usage Tracking
```python
# Track AI queries
def track_ai_query(user_id):
    user = User.query.get(user_id)
    if user.ai_query_limit > 0:  # Not unlimited
        if user.ai_queries_used >= user.ai_query_limit:
            raise QuotaExceeded('AI query limit reached')
        user.ai_queries_used += 1
        db.session.commit()
    
    # Log usage
    log = UsageLog(
        user_id=user_id,
        action_type='ai_query',
        timestamp=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
```

---

## Key Recommendations Summary

### ✅ Your Spec is Solid
- Clear tier progression
- Appropriate feature gating
- Competitive pricing
- Good upsell path

### 🎯 Immediate Actions
1. Implement subscription_plans table with your 4 tiers
2. Add authentication and role-based access control
3. Create campaign workspace isolation
4. Add feature flags throughout the codebase
5. Integrate Stripe for billing

### 💡 Enhancements to Consider
1. **FREE Tier**: View-only access to 1 district (lead generation)
2. **Usage-based Consultant Pricing**: $450 base + $50/campaign or $10/user
3. **Add-ons**: Extra AI queries, additional territories, white-label branding
4. **Trial Period**: 14-day free trial for all paid tiers
5. **Non-profit Discount**: 50% off for verified non-profits

### 🚀 Feature Gaps to Fill
**High Priority** (needed for launch):
- Campaign workspace management
- List building UI
- Export functionality with limits
- Basic volunteer tracking

**Medium Priority** (post-launch):
- Fundraising module
- Advanced contact tracking
- Multi-campaign dashboard
- Integration APIs

**Low Priority** (future):
- White-label capabilities
- Mobile app
- Advanced analytics
- Predictive modeling

---

## Next Steps

1. **Review and approve** this analysis
2. **Prioritize** which tier to launch first (recommend: Individual + Candidate)
3. **Design** database schema and implement tables
4. **Build** authentication and subscription management
5. **Integrate** Stripe for payments
6. **Add** feature flags throughout existing code
7. **Test** with beta users from each tier
8. **Launch** with marketing campaign

Let me know if you want me to start implementing any of these components!
