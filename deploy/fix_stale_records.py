#!/usr/bin/env python3
"""Delete stale 2026-02-25 election records and regenerate DEM GeoJSON with correct flips."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Count before
before = conn.execute(
    "SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-02-25'"
).fetchone()[0]
print(f"Stale 2026-02-25 records: {before}")

# Delete them
conn.execute("DELETE FROM voter_elections WHERE election_date='2026-02-25'")
conn.commit()

after = conn.execute(
    "SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-02-25'"
).fetchone()[0]
print(f"After delete: {after}")

# Verify remaining elections
rows = conn.execute("""
    SELECT election_date, party_voted, COUNT(*)
    FROM voter_elections
    WHERE election_date LIKE '2026%'
    GROUP BY election_date, party_voted
    ORDER BY election_date, party_voted
""").fetchall()
print("\n2026 election records remaining:")
for r in rows:
    print(f"  {r[0]} | {r[1]}: {r[2]:,}")

print("\nDone. Now need to regenerate DEM GeoJSON with correct flip detection.")
