#!/usr/bin/env python3
"""
Final comprehensive fix:
1. Clear all existing district assignments
2. Reassign using precinct data with flexible matching
3. Verify D15 accuracy
"""
import sqlite3
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
TARGET_D15 = 54573

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

log("="*80)
log("FINAL COMPREHENSIVE DISTRICT FIX")
log("="*80)

conn = sqlite3.connect(DB_PATH, timeout=120.0)
conn.execute('PRAGMA journal_mode=WAL')
cursor = conn.cursor()

# Step 1: Clear all existing assignments
log("\n[1] Clearing all existing district assignments...")
cursor.execute("""
    UPDATE voters
    SET congressional_district = NULL,
        state_senate_district = NULL,
        state_house_district = NULL
""")
cleared = cursor.rowcount
log(f"  ✓ Cleared {cleared:,} voters")
conn.commit()

# Step 2: Create flexible precinct matching function
log("\n[2] Reassigning using precinct data with flexible matching...")

# Try multiple matching strategies
strategies = [
    # Strategy 1: Exact match
    ("Exact match", """
        UPDATE voters
        SET 
            congressional_district = (
                SELECT pd.congressional_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = voters.precinct
            ),
            state_senate_district = (
                SELECT pd.state_senate_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = voters.precinct
            ),
            state_house_district = (
                SELECT pd.state_house_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = voters.precinct
            )
        WHERE congressional_district IS NULL
        AND EXISTS (
            SELECT 1 FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND pd.precinct = voters.precinct
        )
    """),
    
    # Strategy 2: Strip leading zeros from both sides
    ("Strip leading zeros", """
        UPDATE voters
        SET 
            congressional_district = (
                SELECT pd.congressional_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND LTRIM(pd.precinct, '0') = LTRIM(voters.precinct, '0')
                LIMIT 1
            ),
            state_senate_district = (
                SELECT pd.state_senate_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND LTRIM(pd.precinct, '0') = LTRIM(voters.precinct, '0')
                LIMIT 1
            ),
            state_house_district = (
                SELECT pd.state_house_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND LTRIM(pd.precinct, '0') = LTRIM(voters.precinct, '0')
                LIMIT 1
            )
        WHERE congressional_district IS NULL
        AND voters.precinct IS NOT NULL
        AND voters.precinct != ''
        AND EXISTS (
            SELECT 1 FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND LTRIM(pd.precinct, '0') = LTRIM(voters.precinct, '0')
        )
    """),
    
    # Strategy 3: Pad voter precinct to 4 digits
    ("Pad to 4 digits", """
        UPDATE voters
        SET 
            congressional_district = (
                SELECT pd.congressional_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = SUBSTR('0000' || LTRIM(voters.precinct, '0'), -4)
                LIMIT 1
            ),
            state_senate_district = (
                SELECT pd.state_senate_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = SUBSTR('0000' || LTRIM(voters.precinct, '0'), -4)
                LIMIT 1
            ),
            state_house_district = (
                SELECT pd.state_house_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = SUBSTR('0000' || LTRIM(voters.precinct, '0'), -4)
                LIMIT 1
            )
        WHERE congressional_district IS NULL
        AND voters.precinct IS NOT NULL
        AND voters.precinct != ''
        AND EXISTS (
            SELECT 1 FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND pd.precinct = SUBSTR('0000' || LTRIM(voters.precinct, '0'), -4)
        )
    """)
]

total_updated = 0
for strategy_name, query in strategies:
    log(f"\n  Trying: {strategy_name}...")
    cursor.execute(query)
    updated = cursor.rowcount
    total_updated += updated
    log(f"    ✓ Updated {updated:,} voters")
    conn.commit()

log(f"\n  Total updated: {total_updated:,}")

# Check coverage
cursor.execute("SELECT COUNT(*) FROM voters")
total_voters = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM voters WHERE congressional_district IS NOT NULL")
with_district = cursor.fetchone()[0]

coverage = 100 * with_district / total_voters if total_voters > 0 else 0
log(f"\n✓ District coverage: {with_district:,}/{total_voters:,} ({coverage:.1f}%)")

# Step 3: Verify D15
log("\n" + "="*80)
log("D15 ACCURACY VERIFICATION")
log("="*80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))

actual = cursor.fetchone()[0]
diff = actual - TARGET_D15
accuracy = 100 * (1 - abs(diff) / TARGET_D15) if TARGET_D15 > 0 else 0

log(f"\nD15 Democratic Primary:")
log(f"  Database: {actual:,}")
log(f"  Official: {TARGET_D15:,}")
log(f"  Difference: {diff:+,}")
log(f"  Accuracy: {accuracy:.2f}%")

if accuracy >= 99.9:
    log("  ✓ EXCELLENT - Within 0.1%!")
elif accuracy >= 99.0:
    log("  ✓ GOOD - Within 1%")
elif accuracy >= 95.0:
    log("  ⚠ ACCEPTABLE - Within 5%")
else:
    log("  ✗ NEEDS WORK - More than 5% off")

# Show D15 breakdown
log("\nD15 voters by county:")
cursor.execute("""
    SELECT v.county, COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    GROUP BY v.county
    ORDER BY voters DESC
""", (ELECTION_DATE,))

d15_total = 0
for county, voters in cursor.fetchall():
    log(f"  {county:<20} {voters:>6,}")
    d15_total += voters

log(f"  {'TOTAL':<20} {d15_total:>6,}")

conn.close()

log("\n" + "="*80)
log("COMPLETE!")
log("="*80)

if accuracy >= 95.0:
    log("\n✓ District assignments are accurate enough for production use")
    log("  Next step: Regenerate district caches")
else:
    log("\n⚠ District assignments need further refinement")
    log("  The precinct data may not cover all voters")
