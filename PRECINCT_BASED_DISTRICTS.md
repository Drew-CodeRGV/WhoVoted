# Precinct-Based District Queries

## The Problem
District reports (like TX-15 Congressional District) need to determine which voters fall within the district boundaries. The current approach:

1. **Point-in-polygon checks**: For each voter, check if their lat/lng coordinates fall within the district polygon
2. **Requires geocoding**: Only works for voters with geocoded addresses
3. **Very slow**: Checking millions of coordinates against complex polygons takes 10-60 seconds
4. **Incomplete data**: Many voters don't have geocoded addresses

## The Solution: Precinct-Based Lookups

Instead of checking individual voter coordinates, we can use **precinct boundaries**:

### How It Works

1. **One-time computation** (run once, or when districts change):
   - Load all district boundaries (congressional, state house, commissioner)
   - Load all precinct boundaries
   - Determine which precincts fall within each district
   - Save mapping: `district_name → [precinct_ids]`

2. **Fast queries** (every time a user clicks a district):
   - Look up precincts for that district
   - Query: `SELECT * FROM voters WHERE precinct IN ('101', '102', '103', ...)`
   - No point-in-polygon checks needed!
   - Works for ALL voters (not just geocoded ones)

### Advantages

✅ **Fast**: Simple SQL `IN` query instead of complex geometry calculations  
✅ **Complete**: Works for all voters, not just those with geocoded addresses  
✅ **Accurate**: Uses official precinct boundaries from voter rolls  
✅ **Cacheable**: Precinct mappings rarely change (only with redistricting)  
✅ **Scalable**: Query time is constant regardless of district size  

### Implementation Steps

1. **Run the mapping script**:
   ```bash
   python3 deploy/build_precinct_district_mapping.py
   ```
   This creates: `/opt/whovoted/public/cache/precinct_district_mapping.json`

2. **Update backend queries**:
   - Modify `_lookup_vuids_by_polygon()` to use precinct lookups
   - Add fallback to point-in-polygon for voters without precinct data

3. **Regenerate district caches**:
   - Use precinct-based queries to generate complete district reports
   - Cache files will be accurate and complete

### Data Structure

**Precinct Mapping File** (`precinct_district_mapping.json`):
```json
{
  "TX-15 Congressional District": {
    "district_id": "TX-15",
    "district_type": "congressional",
    "precincts": ["101", "102", "103", "201", "202", ...],
    "precinct_count": 245
  },
  "TX State House District 41": {
    "district_id": "41",
    "district_type": "state_house",
    "precincts": ["301", "302", "303", ...],
    "precinct_count": 87
  }
}
```

### Precinct Overlap Detection

The script uses two methods to determine if a precinct belongs to a district:

1. **Centroid method** (fast): Check if precinct's center point is inside district
2. **Overlap method** (accurate): Check if ≥50% of precinct area overlaps with district

This handles edge cases where precincts span district boundaries.

### Database Schema

Both tables have precinct information:

**voters table**:
- `precinct TEXT` - Voter's registered precinct

**voter_elections table**:
- `precinct TEXT` - Precinct where they voted (may differ from registration)

### Query Example

**Before** (slow, point-in-polygon):
```sql
SELECT ve.vuid FROM voter_elections ve
JOIN voters v ON ve.vuid = v.vuid
WHERE ve.election_date = '2026-03-03'
  AND v.lat BETWEEN 26.0 AND 27.0
  AND v.lng BETWEEN -98.5 AND -97.5
  -- Then check each point against polygon in Python
```

**After** (fast, precinct-based):
```sql
SELECT ve.vuid FROM voter_elections ve
JOIN voters v ON ve.vuid = v.vuid
WHERE ve.election_date = '2026-03-03'
  AND v.precinct IN ('101', '102', '103', '201', '202', ...)
```

### Performance Comparison

| Method | TX-15 (41K voters) | TX-34 (small) | Notes |
|--------|-------------------|---------------|-------|
| Point-in-polygon | 30-60 seconds | 5-10 seconds | Depends on voter count |
| Precinct-based | <1 second | <1 second | Constant time |

### Maintenance

- **Redistricting**: Re-run mapping script when district boundaries change
- **New precincts**: Re-run if new precinct boundaries are added
- **Verification**: Script shows unmapped precincts for manual review

### Fallback Strategy

For voters without precinct data (rare), the system can:
1. Try precinct-based lookup first (fast)
2. Fall back to geocoded point-in-polygon (slower but works)
3. Exclude voters with neither precinct nor coordinates

This ensures maximum coverage while maintaining speed.
