# Tasks: Subscription System (4-Tier SaaS)

## Phase 1: Core Infrastructure

- [ ] **1.1** Add `subscription_plans`, `campaigns`, `campaign_users`, `saved_lists`, `usage_logs` tables to `database.py`
- [ ] **1.2** Add subscription columns to `users` table via `_run_migrations()`
- [ ] **1.3** Seed `subscription_plans` with 4 tiers and correct pricing/flags
- [ ] **1.4** Create `backend/billing.py` with Stripe customer + subscription CRUD
- [ ] **1.5** Add `POST /api/billing/webhook` route to `app.py`
- [ ] **1.6** Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` to `.env`
- [ ] **1.7** Create Stripe Products and Prices for all 4 tiers (monthly + annual); store price IDs in DB

## Phase 2: Access Control

- [ ] **2.1** Add `get_user_plan(user_id)` to `subscription.py`
- [ ] **2.2** Add `require_subscription(min_tier)` decorator
- [ ] **2.3** Add `require_feature(feature_name)` decorator
- [ ] **2.4** Add `check_usage_limit()` and `track_usage()` functions
- [ ] **2.5** Gate AI query endpoint (`/api/llm-query`) with usage tracking
- [ ] **2.6** Gate export endpoints with `require_feature('can_export_data')`
- [ ] **2.7** Inject `window.__userPlan` into HTML responses for authenticated users

## Phase 3: Campaign Workspaces

- [ ] **3.1** Create `backend/campaigns.py` with campaign CRUD
- [ ] **3.2** Add campaign API routes to `app.py`
- [ ] **3.3** Enforce `max_campaigns` limit on campaign creation
- [ ] **3.4** Add campaign member management endpoints
- [ ] **3.5** Build campaign creation/management UI (frontend)

## Phase 4: Subscription UI

- [ ] **4.1** Create `/subscribe` page with tier comparison table
- [ ] **4.2** Stripe Checkout integration for plan selection
- [ ] **4.3** Account page: show current plan, billing period, next renewal
- [ ] **4.4** Upgrade/downgrade flow
- [ ] **4.5** Cancellation flow with immediate access revocation

## Phase 5: Admin Dashboard

- [ ] **5.1** Add subscription management tab to admin dashboard
- [ ] **5.2** Show all subscribers with tier, status, revenue
- [ ] **5.3** Manual comp/override for any user
- [ ] **5.4** Usage analytics (AI queries, exports per user)

## Phase 6: Deploy & Test

- [ ] **6.1** Run schema migration on production
- [ ] **6.2** Configure Stripe webhook in Stripe Dashboard
- [ ] **6.3** Test each tier's feature access
- [ ] **6.4** Test cancellation and access revocation
- [ ] **6.5** Test annual billing discount

## Status

**Overall**: [pending] — design complete, no implementation started.

The per-election credit system (separate spec: `election-subscription-paywall`) is partially implemented and should not be confused with this spec.
