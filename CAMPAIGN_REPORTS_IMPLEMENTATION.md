# Campaign Reports System Implementation

## Overview
Replacing the map legend icon with a comprehensive campaign reports system that provides actionable intelligence for campaigns.

## Phase 1: Priority Reports (Implementing Now)

### 1. Precinct Performance Report
**Purpose:** Identify high/low turnout precincts for resource allocation
**Data:**
- Precinct ID and name
- Total registered voters
- Total votes cast
- Turnout percentage
- Ranking (highest to lowest)
- Party breakdown (Dem/Rep votes and percentages)

**Export:** CSV with all precincts ranked by turnout

### 2. Party Switchers Report
**Purpose:** Target voters who changed party affiliation
**Data:**
- Voter name
- Address (full street address)
- Previous party voted
- Current party voted
- Precinct
- Age/gender (if available)

**Export:** CSV with full contact information for door-knocking/phone banking

### 3. Turf Cuts (Non-Voters Report)
**Purpose:** Generate walk lists for GOTV canvassing
**Data:**
- Voter name
- Full address
- Precinct
- Registration date
- Last voted (election date)
- Voting history score (how often they vote)
- Age/gender

**Filters:**
- By precinct
- By street/neighborhood
- By voting history (sporadic vs never voted)

**Export:** CSV formatted for walk list apps (MiniVAN, etc.)

### 4. New Voter Report
**Purpose:** Identify and activate first-time voters
**Data:**
- Voter name
- Address
- Party voted
- Precinct
- Age
- Registration date

**Export:** CSV for targeted outreach

## UI Changes

### Replace Map Icon
- Change from `fa-map` to `fa-chart-bar` or `fa-file-alt` (reports icon)
- Update title from "Map Options" to "Campaign Reports"
- Keep same positioning (bottom right)

### Reports Modal Structure
```
Campaign Reports
├── Precinct Performance
│   ├── View Report (table)
│   └── Download CSV
├── Party Switchers
│   ├── Filter: D→R / R→D / Both
│   ├── View Report (table with addresses)
│   └── Download CSV
├── Turf Cuts (Non-Voters)
│   ├── Filter: Precinct, Street, Voting History
│   ├── View Report (table)
│   └── Download Walk List CSV
└── New Voters
    ├── Filter: Party, Precinct
    ├── View Report (table)
    └── Download CSV
```

## Backend Endpoints

### `/api/reports/precinct-performance`
**Parameters:**
- `county` (required)
- `election_date` (required)

**Returns:** JSON array of precincts with turnout stats

### `/api/reports/party-switchers`
**Parameters:**
- `county` (required)
- `election_date` (required)
- `direction` (optional: 'd2r', 'r2d', 'both')

**Returns:** JSON array of voters with full details

### `/api/reports/non-voters`
**Parameters:**
- `county` (required)
- `precinct` (optional)
- `street` (optional)
- `voting_history` (optional: 'never', 'sporadic', 'all')

**Returns:** JSON array of registered non-voters

### `/api/reports/new-voters`
**Parameters:**
- `county` (required)
- `election_date` (required)
- `party` (optional: 'Democratic', 'Republican', 'both')

**Returns:** JSON array of first-time voters

## Privacy & Security
- All reports require authentication
- PII (names, addresses) only accessible to logged-in users
- Rate limiting on CSV exports
- Audit logging of report access

## Files to Create/Modify
1. `public/index.html` - Update icon and add reports modal
2. `public/reports.js` - New file for reports UI logic
3. `public/reports.css` - New file for reports styling
4. `backend/app.py` - Add 4 new report endpoints
5. `backend/reports.py` - New file with report generation logic

## Next Steps
1. Update UI (icon + modal)
2. Create backend endpoints
3. Build frontend report viewers
4. Add CSV export functionality
5. Test with real data
6. Add remaining reports in Phase 2
