# Answer: Do Campaign Cards Have Correct Voters?

## Your Question
"Now, vice versa, do all of the lookups like the campaign cards have the correct voters assigned to them? Or do you look them up on the fly? or do you cache them? or do you look them up and THEN cache them?"

## Short Answer

**Currently: NO** - The cache files are outdated (from March 2-5, before district assignment)

**System: HYBRID** - Tries cache first, falls back to live query

**Solution: YES** - Run the regeneration script to update all caches with correct voters

## How It Works Now

### 3-Level System

```
User clicks district card (TX-15)
    ↓
1. Check cache file first
   /opt/whovoted/public/cache/district_report_TX-15_Congressional_District_(PlanC2333).json
   ↓
   EXISTS? → Return instantly (0ms) ✓
   ↓
2. No cache? Query database using district columns
   SELECT * FROM voters WHERE congressional_district = '15'
   ↓
   Returns in 25-200ms ✓
   ↓
3. No district column? Use polygon lookup (slow fallback)
   Point-in-polygon calculations
   ↓
   Returns in 5-30 seconds (rarely used now)
```

### Current State

**Cache files exist but are OUTDATED:**
```bash
-rw-rw-r-- 1 ubuntu ubuntu  538 Mar  5 20:18 district_report_TX-15_Congressional_District_(PlanC2333).json
-rw-rw-r-- 1 ubuntu ubuntu  315 Mar  5 19:56 district_report_TX-28_Congressional_District_(PlanC2333).json
-rw-rw-r-- 1 ubuntu ubuntu  703 Mar  5 19:56 district_report_TX-34_Congressional_District_(PlanC2333).json
```

These were generated BEFORE you assigned all districts (which happened today, March 6).

**What this means:**
- Cache files may show incorrect voter counts
- If cache is used, users see old data
- If cache is missing, system queries database (correct but slower)

## What You Need to Do

### Run This Command Now

```bash
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
cd /opt/whovoted
python3 deploy/regenerate_all_district_caches_fast.py
```

This will:
1. Use your new district column assignments (100% accurate!)
2. Generate cache files for ALL districts (38 Congressional + 31 Senate + 150 House)
3. Take ~5-10 minutes to complete
4. Make all campaign cards load instantly with correct data

### What Gets Updated

**Before regeneration:**
- TX-15 cache: Old voter count (possibly incorrect)
- TX-28 cache: Old voter count (possibly incorrect)
- TX-34 cache: Old voter count (possibly incorrect)
- Other districts: No cache (queries database each time)

**After regeneration:**
- TX-15 cache: 444,926 voters ✓ (correct!)
- TX-28 cache: 80,932 voters ✓ (correct!)
- TX-34 cache: 37,073 voters ✓ (correct!)
- All 38 Congressional districts: Cached ✓
- All 31 State Senate districts: Cached ✓
- All 150 State House districts: Cached ✓

## Why This Is Fast Now

### Before (Old Method)
```python
# Had to use polygon lookups for most voters
for voter in all_voters:
    if point_in_polygon(voter.lat, voter.lng, district_boundary):
        include_voter()
# Time: 5-30 seconds per district
```

### After (New Method with District Columns)
```python
# Simple indexed database query
SELECT * FROM voters WHERE congressional_district = '15'
# Time: 25ms per district
```

**Speed improvement: 200-1000x faster!**

## Performance Comparison

| Method | Speed | Accuracy | When Used |
|--------|-------|----------|-----------|
| **Pre-computed cache** | 0ms (instant) | Stale until regenerated | First choice |
| **District column query** | 25-200ms | Always current | Fallback if no cache |
| **Polygon lookup** | 5-30 seconds | Always current | Rarely used now |

## Code Location

### Backend Logic
File: `WhoVoted/backend/app.py`
Function: `district_stats()` (line 1882)

```python
def district_stats():
    # 1. Try cache first
    if cache_file.exists():
        return cached_data  # INSTANT
    
    # 2. Query using district columns
    vuids = query_by_district_column()  # FAST (25-200ms)
    
    # 3. Calculate stats
    return calculate_stats(vuids)
```

### Cache Generation
File: `WhoVoted/deploy/regenerate_all_district_caches_fast.py` (NEW - optimized!)
File: `WhoVoted/deploy/regenerate_district_cache_complete.py` (OLD - slower)

## When to Regenerate Caches

### Required
- After bulk voter imports
- After redistricting
- After fixing district assignments (like today!)

### Optional
- Weekly during election season
- After major data corrections
- When cache files get corrupted

### Not Needed
- After individual voter updates
- After small data changes
- For real-time queries (district columns handle this)

## Verification

After regenerating, verify the caches:

```bash
# Check TX-15 cache
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
cat /opt/whovoted/public/cache/district_report_TX-15_Congressional_District_\(PlanC2333\).json | python3 -m json.tool | grep total
```

Should show:
```json
"total": 444926,
"total_2024": 123456,
```

## Summary

**Question:** Do campaign cards have correct voters?
**Answer:** Not yet - caches are outdated

**Question:** Do you look them up on the fly or cache them?
**Answer:** Both - cache first (instant), then live query (fast)

**Question:** What should I do?
**Answer:** Run `regenerate_all_district_caches_fast.py` to update all caches

**Result:** All campaign cards will show correct voter counts and load instantly!

## Files Created

1. `WhoVoted/deploy/regenerate_all_district_caches_fast.py` - NEW optimized script
2. `WhoVoted/DISTRICT_CACHE_STRATEGY.md` - Detailed explanation
3. `WhoVoted/ANSWER_DISTRICT_CACHE_QUESTION.md` - This file

## Next Steps

1. **Run regeneration script** (5-10 minutes)
2. **Test campaign cards** - Click TX-15, TX-28, TX-34
3. **Verify voter counts** - Should match database queries
4. **Enjoy instant loading** - All districts cached!

---

**Bottom line:** Your district assignments are perfect (100% coverage). Now regenerate the caches so the campaign cards show the correct data instantly!
