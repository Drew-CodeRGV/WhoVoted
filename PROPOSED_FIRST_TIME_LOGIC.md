# Proposed First-Time Voter Logic

## Data Context
Based on your data files:
- **Hidalgo County**: 2022 primary (both parties), 2024 primary (both parties), 2026 primary (current)
- **Other counties**: Likely statewide EVR data for 2026 only
- **Birth years**: Available for most voters

## Proposed Logic: Tiered Approach

### Definition: "First-Time Primary Voter"
A voter who has never voted in ANY primary election (Democratic, Republican, or other) in our database.

### Logic Rules

```python
def is_first_time_voter(voter, election_date, county):
    """
    Determine if a voter is a first-time primary voter.
    
    Returns: (is_first_time: bool, confidence: str)
    """
    
    # 1. Check if voter has ANY prior primary voting history
    has_prior_primary = voter_has_prior_primary_vote(voter.vuid, election_date)
    
    if has_prior_primary:
        # Definitely NOT a first-time voter
        return (False, 'high')
    
    # 2. No prior history in our DB - need to determine confidence
    
    # Check voter's age
    age_at_election = calculate_age(voter.birth_year, election_date)
    
    if age_at_election is None:
        # No birth year - can't determine age
        # Check if county has historical data
        if county_has_complete_history(county, election_date):
            return (True, 'medium')  # Probably first-time
        else:
            return (True, 'low')  # Unknown - might just be missing data
    
    # We have age information
    if age_at_election <= 19:
        # Young voter - very likely first-time
        return (True, 'high')
    
    elif age_at_election <= 25:
        # Young adult - likely first-time (many don't vote until later)
        if county_has_complete_history(county, election_date):
            return (True, 'high')
        else:
            return (True, 'medium')
    
    else:
        # Older voter with no history
        if county_has_complete_history(county, election_date):
            # We have good data - they really haven't voted before
            return (True, 'high')
        else:
            # Missing historical data - uncertain
            return (True, 'low')


def county_has_complete_history(county, election_date):
    """
    Check if we have reliable historical primary data for this county.
    
    "Complete" means we have at least 2 prior primary elections (4+ years of data).
    """
    prior_elections = get_prior_elections_for_county(county, election_date)
    return len(prior_elections) >= 2


def voter_has_prior_primary_vote(vuid, election_date):
    """
    Check if voter has voted in ANY primary before this election.
    """
    return EXISTS(
        SELECT 1 FROM voter_elections
        WHERE vuid = ?
          AND election_date < ?
          AND party_voted IN ('Democratic', 'Republican', 'Libertarian', 'Green')
          AND party_voted != '' AND party_voted IS NOT NULL
    )
```

## Implementation Strategy

### For Your Data:

**Hidalgo County (2026 primary):**
- Has 2022 and 2024 data → `county_has_complete_history = True`
- High confidence for all first-time determinations
- Count anyone with no prior primary history as first-time

**Other Counties (2026 primary):**
- Only have 2026 data → `county_has_complete_history = False`
- Use age-based confidence:
  - Age ≤19: Count as first-time (high confidence)
  - Age 20-25: Count as first-time (medium confidence)
  - Age >25: Count as first-time (low confidence) - flag for review

### Reporting Options

**Option A: Conservative (Recommended)**
Only count high-confidence first-time voters:
```sql
WHERE is_new_voter = 1 
  AND (
    age <= 19 
    OR county_has_complete_history = 1
  )
```

**Option B: Inclusive**
Count all first-time voters but show confidence levels:
```
First-Time Voters: 1,234
  - High confidence: 856 (69%)
  - Medium confidence: 234 (19%)
  - Low confidence: 144 (12%)
```

**Option C: Age-Gated (Simplest)**
Only count voters age 18-22 as "first-time":
```sql
WHERE NOT EXISTS (prior primary vote)
  AND birth_year BETWEEN (election_year - 22) AND (election_year - 18)
```

## Recommended: Conservative Approach

For the 2026 primary, use this logic:

```python
is_first_time = (
    # No prior primary voting history
    NOT EXISTS (prior primary vote)
    
    AND (
        # Either: Young voter (definitely first-time eligible)
        age <= 22
        
        OR
        
        # Or: County has complete history (we can trust the data)
        county IN ('Hidalgo', ...)  # Counties with 2+ prior elections
    )
)
```

### Why This Works:

1. **Hidalgo County**: Count all voters with no prior history (you have 2022, 2024, 2026 data)
2. **Other counties**: Only count young voters (18-22) to avoid false positives
3. **Simple to explain**: "First-time voters are those who haven't voted in our prior elections, focusing on young voters in counties with limited data"
4. **Accurate**: Won't inflate numbers with 50-year-olds who might have voted in 2018 (before your data)

## Implementation Checklist

- [ ] Add `confidence_level` column to voter_elections table
- [ ] Update flag-setting logic in database.py
- [ ] Update stats calculation in database.py
- [ ] Update API endpoints in app.py
- [ ] Update reports in reports.py
- [ ] Add county history check function
- [ ] Regenerate all cached data
- [ ] Update UI to show confidence levels (optional)

## SQL Implementation

```sql
-- Add confidence tracking
ALTER TABLE voter_elections ADD COLUMN new_voter_confidence TEXT;

-- Set is_new_voter flag with confidence
UPDATE voter_elections SET
    is_new_voter = CASE
        WHEN EXISTS (
            SELECT 1 FROM voter_elections ve2
            WHERE ve2.vuid = voter_elections.vuid
              AND ve2.election_date < voter_elections.election_date
              AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
        ) THEN 0
        ELSE 1
    END,
    new_voter_confidence = CASE
        WHEN EXISTS (prior vote) THEN NULL
        WHEN (2026 - birth_year) <= 19 THEN 'high'
        WHEN (2026 - birth_year) <= 25 AND county IN ('Hidalgo') THEN 'high'
        WHEN county IN ('Hidalgo') THEN 'high'
        WHEN (2026 - birth_year) <= 25 THEN 'medium'
        ELSE 'low'
    END
WHERE election_date = '2026-03-03';
```

## For Reporting

**Conservative count (recommended for public-facing numbers):**
```sql
SELECT COUNT(*) FROM voter_elections
WHERE election_date = '2026-03-03'
  AND is_new_voter = 1
  AND new_voter_confidence IN ('high', 'medium')
```

**Full count with breakdown:**
```sql
SELECT 
    new_voter_confidence,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM voter_elections
WHERE election_date = '2026-03-03'
  AND is_new_voter = 1
GROUP BY new_voter_confidence
```
