# Final First-Time Voter Logic

## Definition
A voter is considered a "first-time primary voter" if they meet either of these criteria:

### Rule 1: Age-Based (Newly Eligible)
**The voter was under 18 during all prior elections and is now 18+ and voting**

Example:
- Born in 2008
- 2022 primary: age 14 (too young)
- 2024 primary: age 16 (too young)
- 2026 primary: age 18 ✓ **FIRST-TIME VOTER**

### Rule 2: History-Based (Never Voted Before)
**We have 3+ prior elections for the area AND the voter doesn't appear in any of them**

Example:
- 45 years old
- 2020, 2022, 2024 primaries: no record
- 2026 primary: voted ✓ **FIRST-TIME VOTER**

## SQL Implementation

```sql
-- Check if voter is first-time
is_new_voter = CASE
    WHEN EXISTS (
        -- Has voted in a prior primary
        SELECT 1 FROM voter_elections ve2
        WHERE ve2.vuid = current_voter.vuid
          AND ve2.election_date < current_election_date
          AND ve2.party_voted != '' 
          AND ve2.party_voted IS NOT NULL
    ) THEN 0  -- Not new, has prior history
    
    WHEN (
        -- Rule 1: Was under 18 for all prior elections
        SELECT COUNT(*) FROM voter_elections ve_prior
        WHERE ve_prior.election_date < current_election_date
          AND ve_prior.party_voted != '' 
          AND ve_prior.party_voted IS NOT NULL
          AND (CAST(SUBSTR(ve_prior.election_date, 1, 4) AS INTEGER) - birth_year) >= 18
    ) = 0 
    AND (current_election_year - birth_year) >= 18
    THEN 1  -- New voter: was too young before, now eligible
    
    WHEN (
        -- Rule 2: Area has 3+ prior elections
        SELECT COUNT(DISTINCT ve_area.election_date)
        FROM voter_elections ve_area
        JOIN voters v_area ON ve_area.vuid = v_area.vuid
        WHERE v_area.county = current_voter.county
          AND ve_area.election_date < current_election_date
          AND ve_area.party_voted != ''
          AND ve_area.party_voted IS NOT NULL
    ) >= 3
    THEN 1  -- New voter: area has good history, voter never appeared
    
    ELSE 0  -- Not enough data to determine
END
```

## Python Implementation

```python
def is_first_time_voter(vuid, birth_year, county, election_date, conn):
    """
    Determine if a voter is a first-time primary voter.
    
    Args:
        vuid: Voter unique ID
        birth_year: Year voter was born
        county: County where voter is registered
        election_date: Current election date (YYYY-MM-DD)
        conn: Database connection
        
    Returns:
        bool: True if first-time voter, False otherwise
    """
    
    # Check if voter has ANY prior primary voting history
    has_prior = conn.execute("""
        SELECT 1 FROM voter_elections
        WHERE vuid = ?
          AND election_date < ?
          AND party_voted != '' 
          AND party_voted IS NOT NULL
        LIMIT 1
    """, [vuid, election_date]).fetchone()
    
    if has_prior:
        # Has voted before - NOT a first-time voter
        return False
    
    # No prior history - check if they qualify as first-time
    
    election_year = int(election_date.split('-')[0])
    current_age = election_year - birth_year if birth_year else None
    
    # Rule 1: Check if voter was under 18 for all prior elections
    if current_age and current_age >= 18:
        # Get all prior election dates
        prior_elections = conn.execute("""
            SELECT DISTINCT election_date
            FROM voter_elections
            WHERE election_date < ?
              AND party_voted != '' 
              AND party_voted IS NOT NULL
            ORDER BY election_date
        """, [election_date]).fetchall()
        
        # Check if voter was under 18 for ALL prior elections
        was_too_young_for_all = True
        for prior_election in prior_elections:
            prior_year = int(prior_election[0].split('-')[0])
            age_at_prior = prior_year - birth_year
            if age_at_prior >= 18:
                # Was eligible to vote in at least one prior election
                was_too_young_for_all = False
                break
        
        if was_too_young_for_all and len(prior_elections) > 0:
            # Was under 18 for all prior elections, now 18+ and voting
            return True
    
    # Rule 2: Check if county has 3+ prior elections
    prior_election_count = conn.execute("""
        SELECT COUNT(DISTINCT ve.election_date)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
          AND ve.election_date < ?
          AND ve.party_voted != ''
          AND ve.party_voted IS NOT NULL
    """, [county, election_date]).fetchone()[0]
    
    if prior_election_count >= 3:
        # County has good historical data
        # Voter has no prior history (checked above)
        # Therefore: first-time voter
        return True
    
    # Doesn't meet either criteria
    return False
```

## Simplified Logic for Implementation

```python
def is_first_time_voter_simple(vuid, birth_year, county, election_date, conn):
    """Simplified version for performance."""
    
    # Has prior primary vote? → NOT first-time
    has_prior = conn.execute("""
        SELECT 1 FROM voter_elections
        WHERE vuid = ? AND election_date < ?
          AND party_voted != '' AND party_voted IS NOT NULL
        LIMIT 1
    """, [vuid, election_date]).fetchone()
    
    if has_prior:
        return False
    
    election_year = int(election_date.split('-')[0])
    
    # Rule 1: Was under 18 for earliest prior election?
    if birth_year:
        earliest_election = conn.execute("""
            SELECT MIN(election_date) FROM voter_elections
            WHERE election_date < ?
              AND party_voted != '' AND party_voted IS NOT NULL
        """, [election_date]).fetchone()[0]
        
        if earliest_election:
            earliest_year = int(earliest_election.split('-')[0])
            age_at_earliest = earliest_year - birth_year
            
            if age_at_earliest < 18 and (election_year - birth_year) >= 18:
                # Was too young at earliest election, now eligible
                return True
    
    # Rule 2: County has 3+ prior elections?
    prior_count = conn.execute("""
        SELECT COUNT(DISTINCT ve.election_date)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ? AND ve.election_date < ?
          AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
    """, [county, election_date]).fetchone()[0]
    
    return prior_count >= 3
```

## Examples

### Example 1: Young Voter (Rule 1)
- Birth year: 2008
- 2022 primary exists: age 14 (under 18) ✗
- 2024 primary exists: age 16 (under 18) ✗
- 2026 primary: age 18 ✓
- **Result: FIRST-TIME VOTER** (was too young before)

### Example 2: Older Voter in Well-Documented County (Rule 2)
- Birth year: 1980 (age 46)
- County: Hidalgo
- Prior elections: 2020, 2022, 2024 (3 elections)
- No record in any prior election
- **Result: FIRST-TIME VOTER** (never voted despite being eligible)

### Example 3: Older Voter in Poorly-Documented County
- Birth year: 1980 (age 46)
- County: Brooks
- Prior elections: 2026 only (1 election)
- No record in prior elections
- **Result: NOT FIRST-TIME** (insufficient data - might have voted in 2018)

### Example 4: Voter Who Voted Before
- Birth year: 2000 (age 26)
- Voted in 2024 primary
- **Result: NOT FIRST-TIME** (has prior history)

## County Classification

Based on your data:

**3+ Prior Elections (Rule 2 applies):**
- Hidalgo: 2020(?), 2022, 2024, 2026 → Count all with no prior history

**<3 Prior Elections (Only Rule 1 applies):**
- Most other counties: Only 2026 data → Only count newly eligible voters

## Implementation Steps

1. Update `database.py` flag-setting logic
2. Update `database.py` stats calculation
3. Update `app.py` API endpoints
4. Update `reports.py` report generation
5. Update `processor.py` CSV import
6. Add county prior election count cache
7. Regenerate all cached data
8. Verify with audit script

## Performance Optimization

Cache the county prior election counts:
```python
# At startup or periodically
COUNTY_PRIOR_ELECTION_COUNTS = {
    'Hidalgo': 3,
    'Cameron': 1,
    'Willacy': 1,
    # ... etc
}
```

This avoids repeated queries for the same county.
