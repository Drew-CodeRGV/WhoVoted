# First-Time Voter Logic Fix - Deployment Guide

## Problem
The system was showing 180,809 first-time voters in TX-15, which is clearly inaccurate (almost the entire turnout). The issue was inconsistent logic across different parts of the codebase.

## Solution
Implemented conservative two-rule approach:

### Rule 1: Newly Eligible Voters
Voter was under 18 during ALL prior elections and is now 18+ and voting.

**Example:** Born in 2008, now 18 in 2026 → First-time voter ✓

### Rule 2: Never Voted (High Confidence)
Area has 3+ prior elections in database AND voter doesn't appear in any of them.

**Example:** 45-year-old in Hidalgo County (has 2022, 2024, 2026 data) with no prior history → First-time voter ✓

### Better Safe Than Sorry
If we don't have sufficient data (< 3 prior elections), we DON'T mark voters as new unless they meet Rule 1.

## What Changed

### Files Updated:
1. `backend/database.py`
   - Replaced `_county_has_prior_data()` with `_county_has_sufficient_history()` (checks for 3+ elections)
   - Added `_was_eligible_in_prior_elections()` helper function
   - Updated flag-setting logic in GeoJSON generation
   - Updated stats calculation logic

2. `backend/app.py`
   - Updated API endpoint calculations to use county-specific prior election counts
   - Removed age-range logic (18-19 year olds)
   - Added proper eligibility checking

3. `backend/reports.py`
   - Updated report generation with same logic as API endpoints
   - Ensures consistency across all reporting

### New Files:
- `deploy/fix_new_voter_flags.py` - Script to recalculate all flags in database
- `FINAL_FIRST_TIME_LOGIC.md` - Complete documentation of new logic
- `FIRST_TIME_VOTER_FIX.md` - This deployment guide

## Deployment Steps

### Step 1: Deploy Code Changes
```bash
# On your local machine
cd WhoVoted
git add backend/database.py backend/app.py backend/reports.py
git add deploy/fix_new_voter_flags.py
git add FINAL_FIRST_TIME_LOGIC.md FIRST_TIME_VOTER_FIX.md
git commit -m "Fix first-time voter logic - conservative two-rule approach"
git push

# On server
cd /opt/whovoted
git pull
sudo systemctl restart whovoted
```

### Step 2: Recalculate Database Flags
```bash
# On server
cd /opt/whovoted
python3 deploy/fix_new_voter_flags.py
```

This will:
- Process all elections in the database
- Apply Rule 1 or Rule 2 based on county history
- Show before/after counts
- Take ~2-5 minutes depending on data size

### Step 3: Regenerate Cached Data
```bash
# Regenerate district cache (includes TX-15)
python3 deploy/cache_districts_only.py

# Regenerate county reports
python3 deploy/regenerate_county_report_cache.py

# Regenerate gazette cache
python3 deploy/generate_statewide_gazette_cache.py
```

### Step 4: Verify Results
```bash
# Check TX-15 numbers
python3 -c "
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    result = conn.execute('''
        SELECT COUNT(*) as total,
               SUM(CASE WHEN is_new_voter = 1 THEN 1 ELSE 0 END) as new_voters
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
          AND v.county IN ('Hidalgo', 'Cameron', 'Willacy', 'Brooks')
    ''').fetchone()
    
    print(f'TX-15 Area:')
    print(f'  Total voters: {result[0]:,}')
    print(f'  First-time voters: {result[1]:,} ({result[1]/result[0]*100:.1f}%)')
"
```

Expected results:
- Total voters: ~192,000
- First-time voters: ~5,000-15,000 (3-8%) - much more reasonable!

### Step 5: Test Website
1. Go to https://politiquera.com/
2. Check TX-15 district stats
3. Verify first-time voter numbers are reasonable
4. Check county reports
5. Check gazette view

## Expected Impact

### Before Fix:
- TX-15: 180,809 first-time voters (94% of turnout!) ✗
- Clearly inaccurate

### After Fix:
- TX-15: ~5,000-15,000 first-time voters (3-8% of turnout) ✓
- Realistic numbers
- Conservative approach (better to undercount than overcount)

### County Breakdown:

**Hidalgo County:**
- Has 2022, 2024, 2026 data (3 elections)
- Rule 2 applies: All voters with no prior history counted
- High confidence

**Cameron, Willacy, Brooks:**
- Only have 2026 data (1 election)
- Rule 1 only: Only newly eligible voters counted
- Conservative approach

## Rollback Plan

If something goes wrong:

```bash
# Restore old logic
cd /opt/whovoted
git revert HEAD
sudo systemctl restart whovoted

# Restore old flags (if you have a backup)
sqlite3 /opt/whovoted/data/voters.db < backup.sql
```

## Testing Checklist

- [ ] Code deployed to server
- [ ] Backend service restarted
- [ ] Database flags recalculated
- [ ] District cache regenerated
- [ ] County reports regenerated
- [ ] Gazette cache regenerated
- [ ] Website shows reasonable numbers
- [ ] TX-15 first-time voters < 20,000
- [ ] No errors in logs

## Notes

- This is a conservative approach - we may undercount slightly
- Better to show 10,000 accurate first-time voters than 180,000 inflated ones
- Logic is now consistent across all code locations
- Future data imports will use the new logic automatically
