#!/usr/bin/env python3
"""Verify the precinct mapping and show statistics."""
import json
import sqlite3

# Load mapping
with open('/opt/whovoted/public/cache/precinct_district_mapping.json') as f:
    mapping = json.load(f)

print("=" * 60)
print("Precinct-to-District Mapping Statistics")
print("=" * 60)

print(f"\nTotal districts: {len(mapping)}")

# Show each district
for district_name, data in mapping.items():
    print(f"\n{district_name}:")
    print(f"  District ID: {data['district_id']}")
    print(f"  Type: {data['district_type']}")
    print(f"  Precincts: {data['precinct_count']}")

# Count unique precincts
all_precincts = set()
for data in mapping.values():
    all_precincts.update(data['precincts'])

print(f"\n{'='*60}")
print(f"Total unique precinct IDs mapped: {len(all_precincts)}")

# Check database coverage
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Get voter counts by precinct
print("\nChecking database coverage...")
db_precincts = {}
for row in conn.execute("""
    SELECT precinct, COUNT(*) as cnt 
    FROM voters 
    WHERE precinct IS NOT NULL AND precinct != ''
    GROUP BY precinct
"""):
    db_precincts[row[0]] = row[1]

print(f"Database has {len(db_precincts)} unique precincts")
print(f"Total voters with precinct: {sum(db_precincts.values()):,}")

# Check how many DB precincts are mapped
mapped_db_precincts = set(db_precincts.keys()) & all_precincts
unmapped_db_precincts = set(db_precincts.keys()) - all_precincts

print(f"\nMapped DB precincts: {len(mapped_db_precincts)}")
print(f"Unmapped DB precincts: {len(unmapped_db_precincts)}")

# Count voters in mapped vs unmapped precincts
mapped_voters = sum(db_precincts[p] for p in mapped_db_precincts)
unmapped_voters = sum(db_precincts[p] for p in unmapped_db_precincts)

print(f"\nVoters in mapped precincts: {mapped_voters:,} ({mapped_voters*100/sum(db_precincts.values()):.1f}%)")
print(f"Voters in unmapped precincts: {unmapped_voters:,} ({unmapped_voters*100/sum(db_precincts.values()):.1f}%)")

# Show top unmapped precincts
if unmapped_db_precincts:
    print("\nTop 20 unmapped precincts by voter count:")
    unmapped_sorted = sorted([(p, db_precincts[p]) for p in unmapped_db_precincts], 
                            key=lambda x: x[1], reverse=True)[:20]
    for precinct, cnt in unmapped_sorted:
        print(f"  {precinct:20s} {cnt:6,d} voters")

conn.close()

print("\n" + "=" * 60)
print("✅ Verification Complete")
print("=" * 60)
