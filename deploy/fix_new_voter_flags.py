#!/usr/bin/env python3
"""
Fix new voter flags with correct logic.
Only marks voters as "new" if their county has historical data (2+ prior elections).
"""
import sqlite3
import time

DB_PATH = '/opt/whovoted/data/whovoted.db'

print("\n" + "="*70)
print("Fixing New Voter Flags")
print("="*70)
print("\nThis will reset and recompute is_new_voter flags with correct logic.")
print("Only voters in counties with 2+ prior elections will be marked as new.\n")

conn = sqlite3.connect(DB_PATH)

# Step 1: Reset all new voter flags
print("Step 1: Resetting all new voter flags...", end=' ', flush=True)
t0 = time.time()
conn.execute("UPDATE voter_elections SET is_new_voter = 0")
conn.commit()
print(f"✓ ({time.time()-t0:.1f}s)\n")

# Step 2: Recompute with correct logic
print("Step 2: Recomputing new voter flags (counties with 2+ prior elections only)...")
print("-" * 70)

elections = conn.execute("""
    SELECT DISTINCT election_date 
    FROM voter_elections 
    ORDER BY election_date
""").fetchall()

total_new = 0
for (election_date,) in elections:
    print(f"  Processing {election_date}...", end=' ', flush=True)
    t0 = time.time()
    
    result = conn.execute("""
        UPDATE voter_elections ve
        SET is_new_voter = 1
        WHERE ve.election_date = ?
          AND ve.is_new_voter = 0
          AND NOT EXISTS (
              -- No prior voting history for this voter
              SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid
                AND ve2.election_date < ?
                AND ve2.party_voted != '' 
                AND ve2.party_voted IS NOT NULL
          )
          AND EXISTS (
              -- County has at least 2 prior elections (reliable data)
              SELECT 1 FROM voter_elections ve3
              JOIN voters v3 ON ve3.vuid = v3.vuid
              JOIN voters v_current ON ve.vuid = v_current.vuid
              WHERE v3.county = v_current.county
                AND ve3.election_date < ?
                AND ve3.party_voted != ''
                AND ve3.party_voted IS NOT NULL
              GROUP BY v3.county
              HAVING COUNT(DISTINCT ve3.election_date) >= 2
          )
    """, (election_date, election_date, election_date))
    
    count = result.rowcount
    total_new += count
    print(f"✓ {count:,} new voters ({time.time()-t0:.1f}s)")

conn.commit()

print()
print("="*70)
print(f"✅ Fixed! Total new voters across all elections: {total_new:,}")
print("="*70)
print("\nNew voter counts by election:")

for (election_date,) in elections:
    count = conn.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ? AND is_new_voter = 1
    """, (election_date,)).fetchone()[0]
    print(f"  {election_date}: {count:,}")

print()
conn.close()
