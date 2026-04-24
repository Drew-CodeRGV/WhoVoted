---
inclusion: auto
---

# District Vote Counting - Mandatory Methodology

## CRITICAL RULE
When counting votes for ANY district (congressional, state house, state senate, commissioner, etc.) in ANY county in ANY state:

### The ONLY Correct Approach

1. Load district polygon boundaries from GeoJSON
2. Map voting precincts to districts using point-in-polygon on precinct centroids
3. Count votes ONLY from voters whose `precinct` field matches mapped precincts
4. Query `voter_elections` table for those VUIDs

### NEVER:
- Use approximate lat/lng boundaries
- Use coordinate comparisons (e.g., "lng > -98.12")
- Count voters by their individual coordinates
- Assume precinct assignments without polygon verification

### SQLite Query Pattern
```python
# Get precinct centroids
cur.execute("""
    SELECT precinct, AVG(lat), AVG(lng), COUNT(*)
    FROM voters
    WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""", (county,))

# Map to districts using point_in_polygon()
precinct_to_district = {}
for precinct, lat, lng, count in cur.fetchall():
    for district in districts:
        if point_in_polygon(lng, lat, district['geometry']):
            precinct_to_district[precinct] = district_id

# Count votes
precincts = [p for p, d in precinct_to_district.items() if d == target_district]
placeholders = ','.join('?' * len(precincts))
cur.execute(f"""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ?
""", [county] + precincts + [election_date])
```

This is the proven accurate method used for TX-15 and commissioner precincts.
