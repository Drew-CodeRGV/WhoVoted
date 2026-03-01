#!/usr/bin/env python3
"""Check flip data in GeoJSON and DB - simplified."""
import sqlite3
import json

# First check what's in the DEM GeoJSON
path = '/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json'
with open(path) as f:
    data = json.load(f)

switched = 0
has_prev = 0
for feat in data['features']:
    p = feat['properties']
    if p.get('has_switched_parties'):
        switched += 1
    if p.get('party_affiliation_previous'):
        has_prev += 1

print(f"DEM GeoJSON: {len(data['features'])} features")
print(f"  has_switched_parties=True: {switched}")
print(f"  has party_affiliation_previous: {has_prev}")

# Check DB for R->D flips using a simpler approach
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Get all 2026 DEM voters
dem_vuids = conn.execute(
    "SELECT DISTINCT vuid FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Democratic'"
).fetchall()
print(f"\nDB: {len(dem_vuids)} DEM voters in 2026-03-03")

# Sample 100 and check their previous party
import random
sample = random.sample(dem_vuids, min(100, len(dem_vuids)))
r_to_d = 0
for (vuid,) in sample:
    prev = conn.execute("""
        SELECT party_voted FROM voter_elections
        WHERE vuid=? AND election_date < '2026-03-03'
          AND party_voted != '' AND party_voted IS NOT NULL
        ORDER BY election_date DESC LIMIT 1
    """, (vuid,)).fetchone()
    if prev and prev[0] == 'Republican':
        r_to_d += 1

print(f"Sample of {len(sample)}: {r_to_d} had previous Republican vote")
if r_to_d > 0:
    estimated = int(r_to_d / len(sample) * len(dem_vuids))
    print(f"Estimated R->D flips in full dataset: ~{estimated}")
