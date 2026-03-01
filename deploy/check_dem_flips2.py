#!/usr/bin/env python3
"""Check if DEM file should have R->D flips by querying the DB directly."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Find voters in 2026 DEM primary who previously voted Republican
rows = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve1
    WHERE ve1.election_date = '2026-03-03'
      AND ve1.party_voted = 'Democratic'
      AND EXISTS (
          SELECT 1 FROM voter_elections ve2
          WHERE ve2.vuid = ve1.vuid
            AND ve2.election_date = (
                SELECT MAX(ve3.election_date) FROM voter_elections ve3
                WHERE ve3.vuid = ve1.vuid
                  AND ve3.election_date < '2026-03-03'
                  AND ve3.party_voted != '' AND ve3.party_voted IS NOT NULL
            )
            AND ve2.party_voted = 'Republican'
      )
""").fetchone()
print(f"R->D flips (voters in 2026 DEM who prev voted REP): {rows[0]}")

# Find voters in 2026 REP primary who previously voted Democratic
rows2 = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve1
    WHERE ve1.election_date = '2026-03-03'
      AND ve1.party_voted = 'Republican'
      AND EXISTS (
          SELECT 1 FROM voter_elections ve2
          WHERE ve2.vuid = ve1.vuid
            AND ve2.election_date = (
                SELECT MAX(ve3.election_date) FROM voter_elections ve3
                WHERE ve3.vuid = ve1.vuid
                  AND ve3.election_date < '2026-03-03'
                  AND ve3.party_voted != '' AND ve3.party_voted IS NOT NULL
            )
            AND ve2.party_voted = 'Democratic'
      )
""").fetchone()
print(f"D->R flips (voters in 2026 REP who prev voted DEM): {rows2[0]}")

# Show a few R->D examples
examples = conn.execute("""
    SELECT ve1.vuid, ve2.party_voted as prev_party, ve2.election_date as prev_date
    FROM voter_elections ve1
    JOIN voter_elections ve2 ON ve2.vuid = ve1.vuid
    WHERE ve1.election_date = '2026-03-03'
      AND ve1.party_voted = 'Democratic'
      AND ve2.election_date = (
          SELECT MAX(ve3.election_date) FROM voter_elections ve3
          WHERE ve3.vuid = ve1.vuid
            AND ve3.election_date < '2026-03-03'
            AND ve3.party_voted != '' AND ve3.party_voted IS NOT NULL
      )
      AND ve2.party_voted = 'Republican'
    LIMIT 5
""").fetchall()
print(f"\nR->D examples (should be in DEM GeoJSON with has_switched_parties=True):")
for ex in examples:
    print(f"  VUID={ex[0]}, prev_party={ex[1]}, prev_date={ex[2]}")
