# Data Reconciliation & Self-Healing System

## Critical Requirement
**We cannot afford to show inaccurate data.** When county-level turnout data is uploaded, the system MUST match it against statewide data, identify discrepancies, diagnose root causes, and fix them automatically - working relentlessly until complete while reassessing methods if not yielding results.

## Architecture

### Reconciliation Engine
```
┌─────────────────────────────────────────────────────────┐
│         County Upload Trigger                           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Compare County vs Statewide                    │
│  - Total voters by county                               │
│  - By party, by voting method                           │
│  - Identify exact discrepancies                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Diagnose Root Cause                            │
│  - Missing VUIDs in statewide data?                     │
│  - Duplicate records?                                   │
│  - Wrong district assignments?                          │
│  - Data format issues?                                  │
│  - Timing issues (county has newer data)?              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: Apply Fix Strategy                             │
│  - Strategy A: Re-fetch statewide data                  │
│  - Strategy B: Use county data to fill gaps             │
│  - Strategy C: Fix district assignments                 │
│  - Strategy D: Remove duplicates                        │
│  - Strategy E: Manual review required                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: Verify Fix                                     │
│  - Re-compare numbers                                   │
│  - If still wrong: Try next strategy                    │
│  - If no strategies left: Escalate to admin             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: Log Everything                                 │
│  - What was wrong                                       │
│  - What strategies were tried                           │
│  - What worked                                          │
│  - Final accuracy status                                │
└─────────────────────────────────────────────────────────┘
```

## Reconciliation Table
```sql
CREATE TABLE reconciliation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL,  -- 'COUNTY_UPLOAD', 'AUTO_CHECK', 'MANUAL'
    county TEXT,
    election_date TEXT,
    party TEXT,
    
    -- Expected vs Actual
    expected_total INTEGER,  -- From county upload
    actual_total INTEGER,    -- From database
    discrepancy INTEGER,     -- Difference
    discrepancy_pct REAL,    -- Percentage off
    
    -- Diagnosis
    diagnosis TEXT,          -- Root cause identified
    diagnosis_details TEXT,  -- JSON with specifics
    
    -- Fix attempts
    strategies_tried TEXT,   -- JSON array of strategies
    strategy_succeeded TEXT, -- Which one worked
    attempts_count INTEGER,
    
    -- Resolution
    status TEXT,            -- 'RESOLVED', 'IN_PROGRESS', 'ESCALATED', 'FAILED'
    resolution_time_seconds REAL,
    final_accuracy_pct REAL,
    
    -- Metadata
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    notes TEXT
);

CREATE INDEX idx_reconciliation_status ON reconciliation_log(status, created_at);
CREATE INDEX idx_reconciliation_county ON reconciliation_log(county, election_date);
```

## County Turnout Reference Table
```sql
CREATE TABLE county_turnout_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county TEXT NOT NULL,
    election_date TEXT NOT NULL,
    party TEXT NOT NULL,
    voting_method TEXT,  -- 'early-voting', 'election-day', 'mail-in', 'TOTAL'
    
    official_count INTEGER NOT NULL,  -- From county upload (source of truth)
    database_count INTEGER,           -- Current database count
    verified INTEGER DEFAULT 0,       -- 1 if matches, 0 if not
    last_verified_at TEXT,
    
    source_file TEXT,                 -- Original upload file
    uploaded_by TEXT,                 -- User who uploaded
    uploaded_at TEXT DEFAULT (datetime('now')),
    
    UNIQUE(county, election_date, party, voting_method)
);

CREATE INDEX idx_turnout_ref_verified ON county_turnout_reference(verified, county);
```

## Reconciliation Strategies (In Order)

### Strategy A: Re-fetch Statewide Data
**When**: Statewide data might be incomplete
**Action**: 
- Trigger immediate statewide scraper run
- Wait for completion
- Re-compare numbers

### Strategy B: Fill Gaps from County Data
**When**: County has voters not in statewide data
**Action**:
- Identify VUIDs in county data but not statewide
- Import those specific records
- Mark as 'county-sourced' with verification pending

### Strategy C: Fix District Assignments
**When**: Voters assigned to wrong districts
**Action**:
- Use precinct data to reassign
- Clear incorrect county-level fallbacks
- Verify against county totals

### Strategy D: Remove Duplicates
**When**: Same voter counted multiple times
**Action**:
- Find duplicate VUIDs with different voting_methods
- Keep most authoritative record (statewide > county)
- Remove duplicates

### Strategy E: Data Format Reconciliation
**When**: Parsing or format issues
**Action**:
- Re-parse county upload with different parser
- Check for encoding issues
- Validate VUID formats

### Strategy F: Manual Review Required
**When**: All automated strategies fail
**Action**:
- Create detailed report for admin
- Flag in dashboard with red alert
- Provide diagnostic data for manual investigation
- Block data from being shown publicly until resolved

## Self-Healing Loop
```python
def reconcile_county_data(county, election_date, party, expected_count):
    max_attempts = 10
    attempt = 0
    strategies = [
        RefetchStatewideStrategy(),
        FillGapsStrategy(),
        FixDistrictsStrategy(),
        RemoveDuplicatesStrategy(),
        DataFormatStrategy()
    ]
    
    while attempt < max_attempts:
        # Check current accuracy
        actual_count = get_database_count(county, election_date, party)
        discrepancy = abs(expected_count - actual_count)
        accuracy = 100 * (1 - discrepancy / expected_count)
        
        # Success criteria: within 0.1% or exact match
        if accuracy >= 99.9 or discrepancy == 0:
            log_success(county, accuracy, attempt)
            return True
        
        # Try next strategy
        if attempt < len(strategies):
            strategy = strategies[attempt]
            log_attempt(county, strategy.name, attempt)
            
            result = strategy.execute(county, election_date, party)
            
            if not result.improved:
                # Strategy didn't help, try next
                attempt += 1
                continue
            
            # Strategy helped, verify
            new_accuracy = verify_accuracy(county, election_date, party)
            if new_accuracy >= 99.9:
                log_success(county, new_accuracy, attempt)
                return True
        else:
            # All strategies exhausted
            escalate_to_admin(county, election_date, party, {
                'expected': expected_count,
                'actual': actual_count,
                'discrepancy': discrepancy,
                'strategies_tried': [s.name for s in strategies],
                'final_accuracy': accuracy
            })
            return False
        
        attempt += 1
    
    # Max attempts reached
    escalate_to_admin(county, election_date, party, {
        'reason': 'MAX_ATTEMPTS_EXCEEDED',
        'attempts': max_attempts
    })
    return False
```

## Admin Dashboard Integration

### Reconciliation Status Panel
```
┌─────────────────────────────────────────────────────────┐
│  Data Accuracy Status                                   │
├─────────────────────────────────────────────────────────┤
│  ✓ 253 counties verified (99.6%)                        │
│  ⚠ 1 county in progress (Hidalgo - 98.2% accurate)     │
│  ✗ 0 counties failed                                    │
│                                                          │
│  Last reconciliation: 2 minutes ago                     │
│  Next auto-check: in 3h 58m                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Recent Reconciliation Activity                         │
├─────────────────────────────────────────────────────────┤
│  Hidalgo County - Democratic Primary                    │
│  Expected: 54,573  Actual: 55,078  Off by: 505 (0.9%)  │
│  Status: IN_PROGRESS (Attempt 2/10)                     │
│  Current Strategy: Fix District Assignments             │
│  [View Details] [Force Re-check] [Manual Override]      │
├─────────────────────────────────────────────────────────┤
│  Cameron County - Democratic Primary                    │
│  Expected: 12,450  Actual: 12,450  ✓ EXACT MATCH        │
│  Resolved in 1 attempt (Strategy: Re-fetch Statewide)   │
└─────────────────────────────────────────────────────────┘
```

## Data Quality Gates

### Before Showing Data Publicly
```python
def can_show_data_publicly(county, election_date, party):
    # Check if reconciliation passed
    accuracy = get_reconciliation_accuracy(county, election_date, party)
    
    if accuracy >= 99.9:
        return True, "Data verified"
    
    if accuracy >= 99.0:
        return True, "Data verified (within 1%)"
    
    # Data not accurate enough
    return False, f"Data accuracy only {accuracy:.1f}% - reconciliation in progress"
```

## Implementation Files
1. `deploy/reconciliation_engine.py` - Main reconciliation logic
2. `deploy/strategies/` - Individual fix strategies
3. `backend/reconciliation_api.py` - API endpoints
4. `backend/admin/reconciliation.html` - Admin UI
5. `deploy/auto_reconciliation_check.py` - Runs every hour to verify accuracy

## Key Principles
1. **Zero tolerance for inaccuracy** - Data must match or be flagged
2. **Automated healing** - System tries all strategies automatically
3. **Transparent logging** - Every attempt and result logged
4. **Admin escalation** - If automation fails, admin gets detailed report
5. **Public data gates** - Inaccurate data never shown to users
6. **Continuous verification** - Regular auto-checks even after resolution
