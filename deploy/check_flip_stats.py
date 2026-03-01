#!/usr/bin/env python3
"""Check flip stats in GeoJSON files vs DB."""
import sys, os, json, glob
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
db.init_db()
conn = db.get_connection()

print("=== FLIP STATS FROM DB ===")
# Per-election flips from DB
dates = conn.execute("SELECT DISTINCT election_date FROM voter_elections ORDER BY election_date").fetchall()
for d in dates:
    ed = d[0]
    flips = conn.execute("""
        SELECT COUNT(*) FROM voter_elections ve_current
        JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
        WHERE ve_current.election_date = ?
            AND ve_prev.election_date = (
                SELECT MAX(ve2.election_date) FROM voter_elections ve2
                WHERE ve2.vuid = ve_current.vuid
                    AND ve2.election_date < ve_current.election_date
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
            )
            AND ve_current.party_voted != '' AND ve_current.party_voted IS NOT NULL
            AND ve_prev.party_voted != '' AND ve_prev.party_voted IS NOT NULL
            AND ve_current.party_voted != ve_prev.party_voted
    """, (ed,)).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = ?", (ed,)).fetchone()[0]
    print(f"  {ed}: {flips} flips out of {total} voters")

print("\n=== FLIP STATS FROM GEOJSON FILES ===")
for f in sorted(glob.glob("/opt/whovoted/public/data/map_data_*.json")):
    with open(f) as fh:
        data = json.load(fh)
    features = data.get("features", [])
    flipped = sum(1 for feat in features if feat.get("properties", {}).get("has_switched_parties"))
    total = len(features)
    basename = os.path.basename(f)
    if flipped > 0 or "2026" in basename or "2024" in basename:
        print(f"  {basename}: {flipped} flipped / {total} total")

print("\n=== SAMPLE FLIPPED VOTERS IN 2026-03-03 ===")
# Check what the generate_geojson_for_election produces
geojson_dem = db.generate_geojson_for_election('Hidalgo', '2026-03-03', 'Democratic', 'early-voting')
geojson_rep = db.generate_geojson_for_election('Hidalgo', '2026-03-03', 'Republican', 'early-voting')
dem_flips = sum(1 for f in geojson_dem['features'] if f['properties'].get('has_switched_parties'))
rep_flips = sum(1 for f in geojson_rep['features'] if f['properties'].get('has_switched_parties'))
print(f"  DEM 2026-03-03: {dem_flips} flipped / {len(geojson_dem['features'])} total")
print(f"  REP 2026-03-03: {rep_flips} flipped / {len(geojson_rep['features'])} total")

# Also check 2026-02-23
geojson_dem_23 = db.generate_geojson_for_election('Hidalgo', '2026-02-23', 'Democratic', 'early-voting')
geojson_rep_23 = db.generate_geojson_for_election('Hidalgo', '2026-02-23', 'Republican', 'early-voting')
dem_flips_23 = sum(1 for f in geojson_dem_23['features'] if f['properties'].get('has_switched_parties'))
rep_flips_23 = sum(1 for f in geojson_rep_23['features'] if f['properties'].get('has_switched_parties'))
print(f"  DEM 2026-02-23: {dem_flips_23} flipped / {len(geojson_dem_23['features'])} total")
print(f"  REP 2026-02-23: {rep_flips_23} flipped / {len(geojson_rep_23['features'])} total")

# Show a few sample flipped voters from the 2026-03-03 DEM file
print("\n=== SAMPLE FLIPPED VOTERS (DEM 2026-03-03) ===")
count = 0
for feat in geojson_dem['features']:
    p = feat['properties']
    if p.get('has_switched_parties'):
        print(f"  {p['vuid']} {p['name']}: prev={p.get('party_affiliation_previous')} cur={p.get('party_affiliation_current')}")
        count += 1
        if count >= 5:
            break

print("\n=== CHECKING: what election_date does the 20260224 day-snapshot use? ===")
# The regen_stale_geojson.py used election_date='2026-03-03' to regenerate the 20260224 files
# But the ORIGINAL 20260223 files used election_date='2026-02-23'
# The issue might be that 2026-03-03 voters have a different preceding election than 2026-02-23 voters
# Let's check: for 2026-03-03, what's the immediately preceding election?
prev = conn.execute("""
    SELECT DISTINCT ve_prev.election_date, COUNT(*)
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid
                AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
        )
    GROUP BY ve_prev.election_date
""").fetchall()
print("  Preceding elections for 2026-03-03 voters:")
for r in prev:
    print(f"    {r[0]}: {r[1]} voters")
