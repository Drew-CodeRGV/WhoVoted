#!/usr/bin/env python3
"""
How many people voted in the McAllen ISD Bond (May 10, 2026) 
but did NOT vote in the March 3, 2026 primary?

These are voters who showed up for the bond but skipped the primary —
potential mobilization targets for the runoff.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)

# Voters who voted in the bond election
bond_voters = conn.execute("""
    SELECT COUNT(DISTINCT vuid) FROM voter_elections
    WHERE election_date = '2026-05-10'
""").fetchone()[0]

# Voters who voted in the March primary
primary_voters = conn.execute("""
    SELECT COUNT(DISTINCT vuid) FROM voter_elections
    WHERE election_date = '2026-03-03'
""").fetchone()[0]

# Voters who voted in the bond BUT NOT in the primary
bond_not_primary = conn.execute("""
    SELECT COUNT(DISTINCT ve_bond.vuid)
    FROM voter_elections ve_bond
    WHERE ve_bond.election_date = '2026-05-10'
    AND ve_bond.vuid NOT IN (
        SELECT vuid FROM voter_elections WHERE election_date = '2026-03-03'
    )
""").fetchone()[0]

# Of those, how many are in HD-41?
bond_not_primary_hd41 = conn.execute("""
    SELECT COUNT(DISTINCT ve_bond.vuid)
    FROM voter_elections ve_bond
    INNER JOIN voters v ON ve_bond.vuid = v.vuid
    WHERE ve_bond.election_date = '2026-05-10'
    AND v.state_house_district = 'HD-41'
    AND ve_bond.vuid NOT IN (
        SELECT vuid FROM voter_elections WHERE election_date = '2026-03-03'
    )
""").fetchone()[0]

# Breakdown: of the bond-not-primary voters in HD-41, what's their party history?
party_breakdown = conn.execute("""
    SELECT v.current_party, COUNT(DISTINCT v.vuid) as cnt
    FROM voters v
    INNER JOIN voter_elections ve_bond ON v.vuid = ve_bond.vuid
    WHERE ve_bond.election_date = '2026-05-10'
    AND v.state_house_district = 'HD-41'
    AND v.vuid NOT IN (
        SELECT vuid FROM voter_elections WHERE election_date = '2026-03-03'
    )
    GROUP BY v.current_party
    ORDER BY cnt DESC
""").fetchall()

conn.close()

print(f"McAllen ISD Bond (May 10, 2026): {bond_voters:,} voters")
print(f"March 3 Primary: {primary_voters:,} voters")
print(f"\nVoted in Bond but NOT in Primary: {bond_not_primary:,}")
print(f"  Of those, in HD-41: {bond_not_primary_hd41:,}")
print(f"\nHD-41 Bond-not-Primary breakdown by party history:")
for party, cnt in party_breakdown:
    print(f"  {party or 'No party history'}: {cnt:,}")
