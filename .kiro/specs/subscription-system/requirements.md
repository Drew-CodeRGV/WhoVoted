# Spec: Subscription System (4-Tier SaaS)

## Problem

WhoVoted has no recurring revenue model. The per-election credit system ($10/election) is live in the admin portal but the 4-tier SaaS subscription model ($50–$450/mo) — designed for campaigns and consultants who need ongoing access — has not been implemented.

## Users

- **Individual** ($50/mo): Researchers, journalists, super-voters. Read-only access, no exports.
- **Candidate** ($200/mo): Single-race candidate + 2 helpers. Territory-scoped, no list building.
- **Campaign Manager** ($250/mo): Full field ops for one campaign. List building, turf cutting, exports.
- **Consultant** ($450/mo): Multi-campaign management. Cross-campaign analytics, white-label.

## Acceptance Criteria

1. Four subscription tiers exist in `subscription_plans` table with correct pricing and feature flags.
2. Users can subscribe via Stripe (monthly or annual billing).
3. Feature access is enforced server-side via middleware; frontend hides unavailable features.
4. Superadmins (drew@politiquera.com, drew@drewlentz.com) bypass all tier checks.
5. Subscription status is visible in the admin dashboard.
6. Cancellation immediately revokes access (no grace period).
7. Annual billing offers 22% discount vs monthly.
8. AI query limits enforced: Individual = 50/mo, Candidate/Manager/Consultant = unlimited.
9. Export functionality gated to Campaign Manager and above.
10. Campaign workspace creation gated to Campaign Manager and above.
11. Multi-campaign management gated to Consultant only.
12. Usage is tracked in `usage_logs` table.

## Out of Scope (This Spec)

- Per-election credit system (already implemented — see `election-subscription-paywall` spec)
- Volunteer/contact tracking module (Phase 4)
- Fundraising/donor module (Phase 4)
- White-label branding (Phase 5)
- Mobile app

## Relationship to Existing Work

The per-election paywall (`election-subscription-paywall` spec) is a separate, simpler system already partially implemented. The 4-tier SaaS system is additive — it layers campaign workspace and operational tools on top of the existing voter data access.
