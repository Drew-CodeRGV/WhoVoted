# WhoVoted Subscription System - Implementation Plan

## Date: March 6, 2026

## Overview

This document provides a detailed implementation plan for the WhoVoted subscription system based on the user-provided specification. It maps the 4 subscription tiers to our current platform capabilities and outlines the technical work required.

---

## Subscription Tiers Summary

| Tier | Monthly | Annual | Max Territories | Max Campaigns | History | Users |
|------|---------|--------|-----------------|---------------|---------|-------|
| Individual | $50 | $390 | 0 | 0 | 5 years | 1 |
| Candidate | $200 | $1,560 | 1 | 0 | 4 elections | 3 |
| Campaign Manager | $250 | $1,950 | 1 | 1 | Full | 15 |
| Consultant | $450 | $3,510 | Unlimited | 10+ | Full | 50+ |

---

## Feature Mapping to Current Platform

### ✅ Features We Already Have

1. **Interactive Voter Map** - Fully functional with geocoded locations
2. **District Boundaries** - Congressional, State House, Commissioner districts
3. **District Report Cards** - Demographics, party breakdown, age groups, county breakdown
4. **Historical Voting Data** - Multiple elections stored in `voter_elections` table
5. **Precinct Performance Reports** - Turnout rankings, party performance
6. **Party Switchers Identification** - R→D, D→R tracking
7. **New Voter Identification** - First-time primary voters
8. **Turf Cuts / Non-voter Lists** - With geocoded addresses
9. **Walk List Generation** - Optimized routes capability
10. **Export Functionality** - CSV exports
11. **AI Query System** - LLM integration for natural language queries
12. **Data Upload/Import** - Admin dashboard with upload system
13. **Basic Authentication** - Google SSO implemented

### ⚠️ Features That Need Enhancement

1. **Role-Based Access Control (RBAC)** - Need to add subscription tier checking
2. **Campaign Workspace Isolation** - Need campaign object and data scoping
3. **Multi-User Management** - Need team member roles and permissions
4. **Usage Limits Enforcement** - Need to track AI queries, exports, etc.

### ❌ Features We Need to Build

1. **Subscription/Billing System** - Stripe integration
2. **Campaign Object Management** - Create, edit, archive campaigns
3. **Volunteer/Contact Tracking** - Canvass results, responses
4. **Fundraising/Donor Modules** - Donor segments, event tracking
5. **Integration APIs** - Dialers, SMS, CRM connectors
6. **White-Label Capabilities** - Custom branding for consultants
7. **Cross-Campaign Analytics** - Portfolio view for consultants
8. **Saved Lists/Bookmarks** - User-specific saved views

---

## Database Schema

### New Tables Required

```sql
-- Subscription plans configuration
CREATE TABLE subscription_plans (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- 'INDIVIDUAL', 'CANDIDATE', 'CAMPAIGN_MANAGER', 'CONSULTANT'
    display_name TEXT NOT NULL,
    price_monthly REAL NOT NULL,
    price_3_month REAL,
    price_6_month REAL,
    price_annual REAL,
    
    -- Limits
    max_territories INTEGER DEFAULT 0,  -- -1 for unlimited
    max_campaigns INTEGER DEFAULT 0,
    max_users INTEGER DEFAULT 1,
    history_years INTEGER DEFAULT 5,  -- -1 for full
    history_elections INTEGER DEFAULT -1,  -- -1 for full
    ai_query_limit INTEGER DEFAULT 50,  -- -1 for unlimited
    
    -- Feature flags
    can_create_campaign BOOLEAN DEFAULT 0,
    can_manage_multiple_campaigns BOOLEAN DEFAULT 0,
    can_build_lists BOOLEAN DEFAULT 0,
    can_cut_turf BOOLEAN DEFAULT 0,
    can_export_data BOOLEAN DEFAULT 0,
    can_manage_volunteers BOOLEAN DEFAULT 0,
    can_track_fundraising BOOLEAN DEFAULT 0,
    has_advanced_reporting BOOLEAN DEFAULT 0,
    has_cross_campaign_reporting BOOLEAN DEFAULT 0,
    can_white_label BOOLEAN DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhance existing users table
ALTER TABLE users ADD COLUMN subscription_plan_id INTEGER REFERENCES subscription_plans(id);
ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'trial';  -- 'trial', 'active', 'expired', 'cancelled'
ALTER TABLE users ADD COLUMN subscription_start DATE;
ALTER TABLE users ADD COLUMN subscription_end DATE;
ALTER TABLE users ADD COLUMN stripe_customer_id TEXT;
ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT;
ALTER TABLE users ADD COLUMN ai_queries_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN ai_queries_reset_date DATE;
ALTER TABLE users ADD COLUMN organization TEXT;

-- Campaigns
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    
    -- Territory definition
    territory_type TEXT NOT NULL,  -- 'congressional', 'state_house', 'commissioner', 'county', 'custom'
    territory_id TEXT,  -- 'TX-15', 'HD-39', 'Hidalgo', etc.
    territory_geojson TEXT,  -- Custom boundary if territory_type='custom'
    
    -- Election info
    election_date DATE,
    election_type TEXT,  -- 'primary', 'general', 'runoff'
    
    -- Status
    status TEXT DEFAULT 'active',  -- 'active', 'archived', 'completed'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP
);

-- Campaign team members
CREATE TABLE campaign_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- 'manager', 'staff', 'volunteer', 'viewer'
    permissions TEXT,  -- JSON of specific permissions
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by INTEGER REFERENCES users(id),
    UNIQUE(campaign_id, user_id)
);

-- Saved lists (for list building)
CREATE TABLE saved_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    
    -- Filter criteria (JSON)
    filters TEXT NOT NULL,  -- {party: 'Democratic', age_min: 18, age_max: 35, precinct: '101', ...}
    
    -- Cached results
    voter_count INTEGER DEFAULT 0,
    last_generated TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Turf assignments
CREATE TABLE turfs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Assignment
    assigned_user_id INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP,
    
    -- Territory definition
    precinct_list TEXT,  -- JSON array of precincts
    voter_count INTEGER DEFAULT 0,
    geometry TEXT,  -- GeoJSON polygon
    
    -- Status
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'archived'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contact tracking (canvassing results)
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    voter_vuid TEXT NOT NULL,
    
    -- Contact details
    contacted_by_user_id INTEGER REFERENCES users(id),
    contact_date TIMESTAMP NOT NULL,
    contact_type TEXT NOT NULL,  -- 'door', 'phone', 'text', 'email'
    
    -- Response
    response TEXT,  -- 'support', 'oppose', 'undecided', 'not_home', 'refused', 'moved'
    support_level INTEGER,  -- 1-5 scale
    notes TEXT,
    
    -- Follow-up
    needs_followup BOOLEAN DEFAULT 0,
    followup_date DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage tracking (for limits enforcement)
CREATE TABLE usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action_type TEXT NOT NULL,  -- 'ai_query', 'export', 'list_build', 'walk_list'
    resource_id TEXT,  -- campaign_id, list_id, etc.
    metadata TEXT,  -- JSON with additional details
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fundraising/donor tracking (basic)
CREATE TABLE donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    voter_vuid TEXT,  -- Link to voter if applicable
    
    -- Donor info
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    
    -- Donation tracking
    total_donated REAL DEFAULT 0,
    last_donation_date DATE,
    donation_count INTEGER DEFAULT 0,
    
    -- Segmentation
    donor_tier TEXT,  -- 'major', 'regular', 'small', 'lapsed'
    tags TEXT,  -- JSON array of tags
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    
    amount REAL NOT NULL,
    donation_date DATE NOT NULL,
    method TEXT,  -- 'check', 'credit_card', 'cash', 'online'
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Implementation Phases

### Phase 1: Core Subscription Infrastructure (Week 1-2)

**Goal**: Set up subscription plans, billing, and basic access control

**Tasks**:
1. Create `subscription_plans` table and seed with 4 tiers
2. Enhance `users` table with subscription fields
3. Integrate Stripe for payment processing
4. Create subscription management UI in admin dashboard
5. Implement middleware for subscription checking
6. Add feature flags throughout codebase

**Files to Modify**:
- `backend/database.py` - Add new tables
- `backend/auth.py` - Add subscription checking functions
- `backend/app.py` - Add subscription middleware
- `backend/admin/dashboard.html` - Add subscription management UI
- `backend/admin/dashboard.js` - Add subscription management logic

**New Files**:
- `backend/billing.py` - Stripe integration
- `backend/subscription.py` - Subscription logic

**Deliverables**:
- Users can sign up and select a subscription tier
- Stripe handles payment processing
- Feature flags control access to functionality
- Admin can manage subscriptions

---

### Phase 2: Campaign Workspaces (Week 3-4)

**Goal**: Implement campaign objects and data isolation

**Tasks**:
1. Create `campaigns` table
2. Create `campaign_users` table for team management
3. Build campaign creation UI
4. Implement data scoping (filter all queries by campaign_id)
5. Add campaign switcher to UI
6. Update all reports to respect campaign context

**Files to Modify**:
- `backend/database.py` - Add campaign tables
- `backend/app.py` - Add campaign context to all queries
- `backend/reports.py` - Filter by campaign_id
- `public/index.html` - Add campaign selector
- `public/data.js` - Add campaign context to API calls
- `public/campaigns.js` - Update to work with campaign context
- `public/reports.js` - Filter by campaign

**New Files**:
- `backend/campaigns.py` - Campaign management logic
- `public/campaign-manager.js` - Campaign management UI

**Deliverables**:
- Users can create campaigns for their territories
- All data is scoped to the active campaign
- Team members can be added to campaigns with roles
- Campaign Manager and Consultant tiers can manage campaigns

---

### Phase 3: List Building & Turf Cutting (Week 5-6)

**Goal**: Build operational tools for campaign management

**Tasks**:
1. Create `saved_lists` table
2. Create `turfs` table
3. Build list builder UI with advanced filters
4. Build turf cutting UI with map interface
5. Add export functionality with format presets
6. Implement walk list generation

**Files to Modify**:
- `backend/database.py` - Add list and turf tables
- `backend/app.py` - Add list/turf API endpoints
- `public/index.html` - Add list builder and turf cutter buttons

**New Files**:
- `backend/lists.py` - List building logic
- `backend/turfs.py` - Turf cutting logic
- `public/list-builder.js` - List builder UI
- `public/turf-cutter.js` - Turf cutting UI
- `public/walk-list-generator.js` - Walk list generation

**Deliverables**:
- Campaign Manager tier can build and save voter lists
- Campaign Manager tier can cut turfs and assign to team
- Export lists in multiple formats (CSV, dialer presets)
- Generate walk lists with optimized routes

---

### Phase 4: Contact & Volunteer Tracking (Week 7-8)

**Goal**: Track field operations and voter contacts

**Tasks**:
1. Create `contacts` table
2. Build contact logging UI (mobile-friendly)
3. Add volunteer management
4. Create activity dashboards
5. Build reporting for doors knocked, contacts made, etc.

**Files to Modify**:
- `backend/database.py` - Add contacts table
- `backend/app.py` - Add contact tracking API
- `backend/reports.py` - Add activity reports

**New Files**:
- `backend/contacts.py` - Contact tracking logic
- `public/contact-logger.js` - Contact logging UI
- `public/volunteer-manager.js` - Volunteer management
- `public/activity-dashboard.js` - Activity reporting

**Deliverables**:
- Team members can log voter contacts
- Track support levels and responses
- View activity dashboards (doors knocked, contacts made)
- Manage volunteers and assignments

---

### Phase 5: Multi-Campaign & Consultant Features (Week 9-10)

**Goal**: Enable consultant tier with multi-campaign management

**Tasks**:
1. Build multi-campaign workspace switcher
2. Create cross-campaign analytics dashboard
3. Add client folders/labels
4. Implement white-label options (logo, branding)
5. Build portfolio view

**Files to Modify**:
- `backend/app.py` - Add cross-campaign queries
- `backend/reports.py` - Add cross-campaign reports
- `public/index.html` - Add campaign switcher

**New Files**:
- `public/portfolio-dashboard.js` - Cross-campaign analytics
- `public/client-manager.js` - Client organization
- `backend/white_label.py` - White-label configuration

**Deliverables**:
- Consultant tier can manage multiple campaigns
- Cross-campaign analytics and reporting
- Client organization with folders/labels
- White-label branding options

---

## Technical Implementation Details

### Middleware for Access Control

```python
# backend/subscription.py

from functools import wraps
from flask import g, jsonify
import database as db

def get_user_subscription(user_id):
    """Get user's subscription plan with all feature flags."""
    with db.get_db() as conn:
        row = conn.execute("""
            SELECT u.*, sp.*
            FROM users u
            LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
            WHERE u.id = ?
        """, (user_id,)).fetchone()
        return dict(row) if row else None

def require_subscription(min_tier='INDIVIDUAL'):
    """Decorator to require a minimum subscription tier."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'session') or not g.session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = g.session.get('user_id')
            subscription = get_user_subscription(user_id)
            
            if not subscription or subscription.get('subscription_status') != 'active':
                return jsonify({'error': 'Active subscription required'}), 403
            
            # Check tier hierarchy
            tier_order = ['INDIVIDUAL', 'CANDIDATE', 'CAMPAIGN_MANAGER', 'CONSULTANT']
            user_tier = subscription.get('name', '')
            if user_tier not in tier_order or tier_order.index(user_tier) < tier_order.index(min_tier):
                return jsonify({'error': f'Upgrade to {min_tier} tier required'}), 403
            
            # Attach subscription to g for use in route
            g.subscription = subscription
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_feature(feature_name):
    """Decorator to require a specific feature flag."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'session') or not g.session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = g.session.get('user_id')
            subscription = get_user_subscription(user_id)
            
            if not subscription or subscription.get('subscription_status') != 'active':
                return jsonify({'error': 'Active subscription required'}), 403
            
            if not subscription.get(feature_name):
                return jsonify({'error': f'Feature not available in your plan'}), 403
            
            g.subscription = subscription
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_usage_limit(user_id, action_type, limit_field):
    """Check if user has exceeded usage limit for an action."""
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False
    
    limit = subscription.get(limit_field, -1)
    if limit == -1:  # Unlimited
        return True
    
    # Get current usage
    with db.get_db() as conn:
        count = conn.execute("""
            SELECT COUNT(*) as count
            FROM usage_logs
            WHERE user_id = ? AND action_type = ?
            AND timestamp >= date('now', 'start of month')
        """, (user_id, action_type)).fetchone()['count']
    
    return count < limit

def track_usage(user_id, action_type, resource_id=None, metadata=None):
    """Track usage of a feature."""
    with db.get_db() as conn:
        conn.execute("""
            INSERT INTO usage_logs (user_id, action_type, resource_id, metadata)
            VALUES (?, ?, ?, ?)
        """, (user_id, action_type, resource_id, metadata))
```

### Usage Examples

```python
# In backend/app.py

from subscription import require_subscription, require_feature, check_usage_limit, track_usage

# Require minimum tier
@app.route('/api/campaign/create', methods=['POST'])
@require_auth
@require_subscription('CAMPAIGN_MANAGER')
def create_campaign():
    # Only Campaign Manager and Consultant can create campaigns
    pass

# Require specific feature
@app.route('/api/export-list', methods=['POST'])
@require_auth
@require_feature('can_export_data')
def export_list():
    # Only tiers with can_export_data=True can export
    user_id = g.session['user_id']
    
    # Check usage limit
    if not check_usage_limit(user_id, 'export', 'export_limit'):
        return jsonify({'error': 'Export limit reached for this month'}), 429
    
    # Track usage
    track_usage(user_id, 'export', resource_id=request.json.get('list_id'))
    
    # Export logic...
    pass

# AI query with usage tracking
@app.route('/api/llm-query', methods=['POST'])
@require_auth
def llm_query():
    user_id = g.session['user_id']
    subscription = get_user_subscription(user_id)
    
    # Check AI query limit
    if not check_usage_limit(user_id, 'ai_query', 'ai_query_limit'):
        limit = subscription.get('ai_query_limit', 0)
        return jsonify({'error': f'AI query limit ({limit}/month) reached. Upgrade for more queries.'}), 429
    
    # Track usage
    track_usage(user_id, 'ai_query')
    
    # Query logic...
    pass
```

---

## Frontend Feature Flags

```javascript
// public/auth.js

let userSubscription = null;

async function loadUserSubscription() {
    const response = await fetch('/api/user/subscription');
    if (response.ok) {
        userSubscription = await response.json();
    }
}

function canAccess(feature) {
    if (!userSubscription) return false;
    return userSubscription.features[feature] === true;
}

function getTierName() {
    return userSubscription?.tier || 'NONE';
}

function showUpgradePrompt(feature, requiredTier) {
    const modal = document.createElement('div');
    modal.className = 'upgrade-modal';
    modal.innerHTML = `
        <div class="upgrade-backdrop"></div>
        <div class="upgrade-content">
            <h2>🚀 Upgrade Required</h2>
            <p>The <strong>${feature}</strong> feature requires the <strong>${requiredTier}</strong> plan.</p>
            <button onclick="window.location.href='/subscription/upgrade'">Upgrade Now</button>
            <button onclick="this.closest('.upgrade-modal').remove()">Maybe Later</button>
        </div>
    `;
    document.body.appendChild(modal);
}

// Usage in UI
if (canAccess('can_export_data')) {
    showExportButton();
} else {
    showLockedExportButton(() => showUpgradePrompt('Export Lists', 'Campaign Manager'));
}
```

---

## Stripe Integration

```python
# backend/billing.py

import stripe
from config import Config

stripe.api_key = Config.STRIPE_SECRET_KEY

def create_customer(email, name):
    """Create a Stripe customer."""
    return stripe.Customer.create(
        email=email,
        name=name,
        metadata={'source': 'whovoted'}
    )

def create_subscription(customer_id, price_id):
    """Create a subscription for a customer."""
    return stripe.Subscription.create(
        customer=customer_id,
        items=[{'price': price_id}],
        payment_behavior='default_incomplete',
        expand=['latest_invoice.payment_intent']
    )

def cancel_subscription(subscription_id):
    """Cancel a subscription."""
    return stripe.Subscription.delete(subscription_id)

def handle_webhook(payload, sig_header):
    """Handle Stripe webhook events."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return False
    except stripe.error.SignatureVerificationError:
        return False
    
    # Handle different event types
    if event['type'] == 'customer.subscription.created':
        # Activate subscription
        pass
    elif event['type'] == 'customer.subscription.deleted':
        # Deactivate subscription
        pass
    elif event['type'] == 'invoice.payment_succeeded':
        # Extend subscription
        pass
    elif event['type'] == 'invoice.payment_failed':
        # Handle failed payment
        pass
    
    return True
```

---

## Next Steps

1. **Review and Approve** this implementation plan
2. **Prioritize** which tier to launch first (recommend: Individual + Candidate)
3. **Set Timeline** for each phase
4. **Assign Resources** (developers, designers, QA)
5. **Create Stripe Account** and configure products/prices
6. **Design UI/UX** for subscription management
7. **Begin Phase 1** implementation

---

## Estimated Timeline

- **Phase 1**: 2 weeks (Core subscription infrastructure)
- **Phase 2**: 2 weeks (Campaign workspaces)
- **Phase 3**: 2 weeks (List building & turf cutting)
- **Phase 4**: 2 weeks (Contact tracking)
- **Phase 5**: 2 weeks (Multi-campaign features)

**Total**: 10 weeks to full implementation

**MVP Launch** (Individual + Candidate tiers): 4 weeks (Phases 1-2)

---

## Questions for User

1. Which tier should we launch first? (Recommend: Individual + Candidate)
2. Do you have a Stripe account set up?
3. What's the priority: speed to market or feature completeness?
4. Should we offer a free trial period? (Recommend: 14 days)
5. Do you want to offer non-profit discounts?
6. What's the maximum number of campaigns for Consultant tier?
7. Should we implement usage-based pricing for Consultant tier?

Ready to start implementation when you give the go-ahead!
