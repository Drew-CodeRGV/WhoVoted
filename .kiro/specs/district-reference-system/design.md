# Design: District Reference System

## Methodology

### Point-in-Polygon Precinct→District Mapping

1. Load district boundaries from GeoJSON
2. For each precinct: calculate centroid as `AVG(lat)`, `AVG(lng)` of all geocoded voters in that precinct
3. Test centroid against each district polygon
4. Build mapping: `precinct → district_id`
5. UPDATE voters SET `{district_type}_district` = district_id WHERE precinct IN (mapped precincts)

### Why Precinct Centroids (Not Individual Voters)

- Precincts are the atomic unit of election administration
- All voters in a precinct are in the same district (by definition)
- Centroid calculation averages out geocoding errors
- Much faster than testing each voter individually

### Why Not Coordinate Comparisons

The prior approach used simple lat/lng bounds (e.g., "if lng > -98.12, it's in TX-15"). This produced wildly wrong counts because district boundaries are irregular polygons, not rectangles.

## Data Sources

### District Boundaries

| District Type | Source | File |
|---------------|--------|------|
| Congressional | Texas Legislative Council (PLANC2333) | `public/data/districts.json` |
| State House | Texas Legislative Council (PLANH2316) | `public/data/districts.json` |
| State Senate | Texas Legislative Council (PLANS2168) | `public/data/districts.json` |
| Commissioner | Hidalgo County GIS | `deploy/commissioner_pct2.geojson` |

### Reference Data

- `data/district_reference/congressional_districts.json` — precinct→CD mapping
- `data/district_reference/state_senate_districts.json` — precinct→SD mapping

## Implementation

### Build Script: `deploy/build_precinct_district_mapping.py`

```python
def build_mapping(district_type, geojson_path, county):
    """Build precinct→district mapping for a given district type."""
    with open(geojson_path) as f:
        districts = json.load(f)['features']
    
    conn = sqlite3.connect(DB_PATH)
    precincts = conn.execute("""
        SELECT precinct, AVG(lat), AVG(lng), COUNT(*)
        FROM voters WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """, (county,)).fetchall()
    
    mapping = {}
    for precinct, lat, lng, count in precincts:
        for district in districts:
            if point_in_polygon(lng, lat, district['geometry']):
                mapping[precinct] = district['properties']['district_id']
                break
    
    # Apply to voters table
    for precinct, district_id in mapping.items():
        conn.execute(f"UPDATE voters SET {district_type}_district = ? WHERE precinct = ? AND county = ?",
                     (district_id, precinct, county))
    conn.commit()
```

### Cache Rebuild: `deploy/regenerate_all_district_caches_fast.py`

Rebuilds `district_counts_cache` table from current voter data.

## Known Issues

### VTD Vintage Problem

Texas VTD (Voting Tabulation District) boundaries are drawn during redistricting. Between redistricting cycles, counties may split or renumber precincts. When a precinct is split, the centroid may fall in the wrong district.

**Mitigation**: For known split precincts, maintain a manual override table.

### Unmapped Precincts

Precincts with no geocoded voters can't have a centroid calculated. These voters get NULL district assignments.

**Mitigation**: Use the statewide voter file's precinct→VTD mapping as a fallback.

### Commissioner Precinct 2 Fix

CPCT2 had a discrepancy because some precincts were incorrectly assigned. The fix was to manually specify the correct precinct list based on certified election results.

## Files Touched

- `deploy/build_precinct_district_mapping.py` — main builder
- `deploy/build_precinct_district_mapping_fast.py` — optimized version
- `deploy/regenerate_all_district_caches_fast.py` — cache rebuild
- `deploy/fix_cpct2_with_correct_precincts.py` — CPCT2 manual fix
- `deploy/build_house_senate_districts.py` — state house/senate builder
- `public/data/districts.json` — GeoJSON boundaries
- `data/district_reference/*.json` — reference data
- `backend/database.py` — `district_counts_cache` table
