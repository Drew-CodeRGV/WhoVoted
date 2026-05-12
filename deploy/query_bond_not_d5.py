#!/usr/bin/env python3
"""
How many voted in the MISD Bond (May 10) but NOT in the D5 city election (May 2),
who live in District 5 (McAllen city commission district)?

These are people who showed up for the bond but skipped the city race 8 days earlier.
"""
import sqlite3, json

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)

# Bond voters who did NOT vote in D5
bond_not_d5 = conn.execute("""
    SELECT COUNT(DISTINCT ve_bond.vuid)
    FROM voter_elections ve_bond
    WHERE ve_bond.election_date = '2026-05-10'
    AND ve_bond.vuid NOT IN (
        SELECT vuid FROM voter_elections WHERE election_date = '2026-05-02'
    )
""").fetchone()[0]

# Of those, how many are in HD-41?
bond_not_d5_hd41 = conn.execute("""
    SELECT COUNT(DISTINCT ve_bond.vuid)
    FROM voter_elections ve_bond
    INNER JOIN voters v ON ve_bond.vuid = v.vuid
    WHERE ve_bond.election_date = '2026-05-10'
    AND v.state_house_district = 'HD-41'
    AND ve_bond.vuid NOT IN (
        SELECT vuid FROM voter_elections WHERE election_date = '2026-05-02'
    )
""").fetchone()[0]

# Now the key question: of those, who lives in D5?
# D5 is defined by the precincts that were in the D5 election
# We know the D5 precincts from the voters who DID vote in D5
d5_precincts = conn.execute("""
    SELECT DISTINCT v.precinct
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE ve.election_date = '2026-05-02' AND v.precinct IS NOT NULL
""").fetchall()
d5_pcts = [r[0] for r in d5_precincts]
print(f"D5 precincts (from voters who voted in D5): {len(d5_pcts)}")
print(f"  Sample: {d5_pcts[:10]}")

# Bond voters NOT in D5 election, who live in a D5 precinct
if d5_pcts:
    ph = ','.join('?' * len(d5_pcts))
    bond_not_d5_in_d5_area = conn.execute(f"""
        SELECT COUNT(DISTINCT ve_bond.vuid)
        FROM voter_elections ve_bond
        INNER JOIN voters v ON ve_bond.vuid = v.vuid
        WHERE ve_bond.election_date = '2026-05-10'
        AND v.precinct IN ({ph})
        AND ve_bond.vuid NOT IN (
            SELECT vuid FROM voter_elections WHERE election_date = '2026-05-02'
        )
    """, d5_pcts).fetchone()[0]
    
    # Party breakdown
    party = conn.execute(f"""
        SELECT v.current_party, COUNT(DISTINCT v.vuid) as cnt
        FROM voters v
        INNER JOIN voter_elections ve_bond ON v.vuid = ve_bond.vuid
        WHERE ve_bond.election_date = '2026-05-10'
        AND v.precinct IN ({ph})
        AND v.vuid NOT IN (
            SELECT vuid FROM voter_elections WHERE election_date = '2026-05-02'
        )
        GROUP BY v.current_party ORDER BY cnt DESC
    """, d5_pcts).fetchall()
    
    # Also check: did they vote in the March primary?
    also_primary = conn.execute(f"""
        SELECT COUNT(DISTINCT v.vuid)
        FROM voters v
        INNER JOIN voter_elections ve_bond ON v.vuid = ve_bond.vuid
        WHERE ve_bond.election_date = '2026-05-10'
        AND v.precinct IN ({ph})
        AND v.vuid NOT IN (SELECT vuid FROM voter_elections WHERE election_date = '2026-05-02')
        AND v.vuid IN (SELECT vuid FROM voter_elections WHERE election_date = '2026-03-03')
    """, d5_pcts).fetchone()[0]
else:
    bond_not_d5_in_d5_area = 0
    party = []
    also_primary = 0

conn.close()

print(f"\n{'='*60}")
print(f"Bond voters (May 10) who did NOT vote in D5 (May 2):")
print(f"  Total (all areas):     {bond_not_d5:,}")
print(f"  In HD-41:              {bond_not_d5_hd41:,}")
print(f"  In D5 precincts:       {bond_not_d5_in_d5_area:,}")
print(f"\nOf those {bond_not_d5_in_d5_area} in D5 area:")
print(f"  Also voted in March primary: {also_primary}")
print(f"  Party breakdown:")
for p, cnt in party:
    print(f"    {p or 'No party history'}: {cnt:,}")
print(f"\nThese are people who live in D5, voted for the bond,")
print(f"but skipped the city commission race 8 days earlier.")
