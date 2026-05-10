# Design: Subscription System (4-Tier SaaS)

## Architecture

Layered on top of the existing Flask/SQLite backend. Stripe handles billing; the backend enforces feature access via decorators. The per-election credit system remains separate.

## Database Schema

### New Tables

```sql
CREATE TABLE subscription_plans (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- 'INDIVIDUAL', 'CANDIDATE', 'CAMPAIGN_MANAGER', 'CONSULTANT'
    display_name TEXT NOT NULL,
    price_monthly_cents INTEGER NOT NULL,
    price_annual_cents INTEGER NOT NULL,
    max_territories INTEGER DEFAULT 0,   -- -1 = unlimited
    max_campaigns INTEGER DEFAULT 0,
    max_users INTEGER DEFAULT 1,
    history_years INTEGER DEFAULT 5,     -- -1 = full
    history_elections INTEGER DEFAULT -1,
    ai_query_limit INTEGER DEFAULT 50,   -- -1 = unlimited
    can_create_campaign INTEGER DEFAULT 0,
    can_manage_multiple_campaigns INTEGER DEFAULT 0,
    can_build_lists INTEGER DEFAULT 0,
    can_cut_turf INTEGER DEFAULT 0,
    can_export_data INTEGER DEFAULT 0,
    can_manage_volunteers INTEGER DEFAULT 0,
    can_track_fundraising INTEGER DEFAULT 0,
    has_advanced_reporting INTEGER DEFAULT 0,
    has_cross_campaign_reporting INTEGER DEFAULT 0,
    can_white_label INTEGER DEFAULT 0,
    stripe_monthly_price_id TEXT,
    stripe_annual_price_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    territory_type TEXT,  -- 'congressional', 'state_house', 'commissioner', 'county'
    territory_id TEXT,    -- 'TX-15', 'HD-39', 'Hidalgo'
    election_date TEXT,
    election_type TEXT,
    status TEXT DEFAULT 'active',  -- 'active', 'archived', 'completed'
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE campaign_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- 'manager', 'staff', 'volunteer', 'viewer'
    added_at TEXT DEFAULT (datetime('now')),
    UNIQUE(campaign_id, user_id)
);

CREATE TABLE saved_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    filters TEXT NOT NULL,  -- JSON
    voter_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action_type TEXT NOT NULL,  -- 'ai_query', 'export', 'list_build', 'walk_list'
    resource_id TEXT,
    metadata TEXT,  -- JSON
    timestamp TEXT DEFAULT (datetime('now'))
);
```

### Users Table Extensions

```sql
ALTER TABLE users ADD COLUMN subscription_plan_id INTEGER REFERENCES subscription_plans(id);
ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'none';  -- 'none', 'trial', 'active', 'expired', 'cancelled'
ALTER TABLE users ADD COLUMN subscription_start TEXT;
ALTER TABLE users ADD COLUMN subscription_end TEXT;
ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT;
ALTER TABLE users ADD COLUMN ai_queries_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN ai_queries_reset_date TEXT;
ALTER TABLE users ADD COLUMN organization TEXT;
```

## Seed Data

```sql
INSERT INTO subscription_plans (name, display_name, price_monthly_cents, price_annual_cents,
    max_territories, max_campaigns, max_users, history_years, history_elections,
    ai_query_limit, can_export_data, can_create_campaign, can_manage_multiple_campaigns,
    can_build_lists, can_cut_turf, can_manage_volunteers, has_advanced_reporting,
    has_cross_campaign_reporting)
VALUES
    ('INDIVIDUAL',       'Individual',       5000,  39000,  0,  0,  1,  5, -1,  50, 0, 0, 0, 0, 0, 0, 0, 0),
    ('CANDIDATE',        'Candidate',       20000, 156000,  1,  0,  3, -1,  4,  -1, 0, 0, 0, 0, 0, 0, 0, 0),
    ('CAMPAIGN_MANAGER', 'Campaign Manager',25000, 195000,  1,  1, 15, -1, -1,  -1, 1, 1, 0, 1, 1, 1, 1, 0),
    ('CONSULTANT',       'Consultant',      45000, 351000, -1, 10, 50, -1, -1,  -1, 1, 1, 1, 1, 1, 1, 1, 1);
```

## Backend Components

### `backend/billing.py` (new)
- `create_stripe_customer(email, name)` → customer_id
- `create_subscription(customer_id, price_id, billing_period)` → subscription
- `cancel_subscription(stripe_subscription_id)` → immediate cancellation
- `handle_webhook(payload, sig_header)` → dispatch to event handlers
- Events: `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`

### `backend/subscription.py` (extend existing)
Add to existing module:
- `get_user_plan(user_id)` → plan dict with all feature flags
- `require_subscription(min_tier)` → decorator
- `require_feature(feature_name)` → decorator
- `check_usage_limit(user_id, action_type, limit_field)` → bool
- `track_usage(user_id, action_type, resource_id, metadata)`

### `backend/campaigns.py` (new)
- `create_campaign(owner_user_id, name, territory_type, territory_id, election_date)`
- `get_user_campaigns(user_id)` — respects tier limits
- `add_campaign_member(campaign_id, user_id, role)`
- `get_campaign_members(campaign_id)`

## Frontend

### Feature Flag Pattern
```javascript
// Set by server on page load
window.__userPlan = { tier: 'CAMPAIGN_MANAGER', features: { can_export_data: true, ... } };

function canAccess(feature) {
    return window.__userPlan?.features?.[feature] === true;
}
```

### Upgrade Prompt
When a gated feature is clicked, show modal: "This feature requires [Tier]. Upgrade at /subscribe."

## Stripe Integration

- One Stripe Product per tier, two Prices each (monthly + annual)
- `stripe_monthly_price_id` and `stripe_annual_price_id` stored in `subscription_plans`
- Webhook endpoint: `POST /api/billing/webhook`
- Env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

## Alternatives Considered

- **Usage-based pricing for Consultant**: Rejected — too complex for current scale.
- **Free tier**: Deferred — the per-election teaser view serves this purpose.
- **Redis for session/usage tracking**: Rejected — SQLite WAL handles current load.

## Files Touched

- `backend/database.py` — new tables, migrations
- `backend/billing.py` — new
- `backend/subscription.py` — extend
- `backend/campaigns.py` — new
- `backend/app.py` — register blueprints, add billing webhook route
- `backend/admin/dashboard.html` — subscription management UI
- `backend/admin/dashboard.js` — subscription management logic
- `public/auth.js` — feature flag loading
