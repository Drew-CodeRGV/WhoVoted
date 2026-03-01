#!/usr/bin/env python3
"""Verify final state of all GeoJSON files."""
import os, json, glob

print("=== ALL GEOJSON FILES IN public/data ===")
for f in sorted(glob.glob("/opt/whovoted/public/data/map_data_*.json")):
    with open(f) as fh:
        data = json.load(fh)
    features = data.get("features", [])
    geocoded = sum(1 for feat in features if feat.get("geometry") is not None)
    flipped = sum(1 for feat in features if feat.get("properties", {}).get("has_switched_parties"))
    new_voters = sum(1 for feat in features if feat.get("properties", {}).get("is_new_voter"))
    print(f"  {os.path.basename(f)}: {len(features)} voters, {geocoded} geocoded, {flipped} flipped, {new_voters} new")

print("\n=== ELECTION DATES IN DB ===")
import sys
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
db.init_db()
conn = db.get_connection()
rows = conn.execute("SELECT DISTINCT election_date, COUNT(*) as cnt FROM voter_elections GROUP BY election_date ORDER BY election_date").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]} records")
