#!/usr/bin/env python3
"""
Reassign all voters using precinct data and verify accuracy
"""
import sqlite3
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
TARGET_D15 = 54573

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def normalize_precinct_for_match(precinct):
    """Try multiple precinct formats for matching"""
    if not precinct:
        return []
    
    p = str(precinct).strip().upper()
    variants = [p]
    
    # Add version without leading zeros
    no_zeros = p.lstrip('0')
    if no_zeros and no_zeros != p:
        variants.append(no_zeros)
    
    # Add version with leading zeros (up to 4 digits)
    if p.isdigit():
        variants.append(p.zfill(4))
    
    return list(set(variants))

log("="*80)
log("REASSIGN ALL VOTERS USING PRECINCT DATA")
log("="*80)

conn = sqlite3.connect(DB_PATH, timeout=120.0)
conn.execute('PRAGMA journal_mode=WAL')
cursor = conn.cursor()

# Get total voters
cursor.execute("SELECT COUNT(*) FROM voters")
total = cursor.fetchone()[0]
log(f"\nTotal voters: {total:,}")

# Update using direct precinct match
log("\nUpdating districts using precinct mappings...")

cursor.execute("""
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
    WHERE EXISTS (
        SELECT 1 FROM precinct_districts pd
        WHERE pd.county = voters.county
        AND pd.precinct = voters.precinct
    )
""")

updated = cursor.rowcount
log(f"✓ Updated {updated:,} voters using exact precinct match")

# Try normalized precinct matching for remaining voters
log("\nTrying normalized precinct matching...")

cursor.execute("""
    UPDATE voters
    SET 
        congressional_district = (
            SELECT pd.congressional_district
            FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND (
                pd.precinct = LTRIM(voters.precinct, '0')
                OR pd.precinct = voters.precinct
                OR LTRIM(pd.precinct, '0') = voters.precinct
            )
            LIMIT 1
        ),
        state_senate_district = (
            SELECT pd.state_senate_district
            FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND (
                pd.precinct = LTRIM(voters.precinct, '0')
                OR pd.precinct = voters.precinct
                OR LTRIM(pd.precinct, '0') = voters.precinct
            )
            LIMIT 1
        ),
        state_house_district = (
            SELECT pd.state_house_district
            FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND (
                pd.precinct = LTRIM(voters.precinct, '0')
                OR pd.precinct = voters.precinct
                OR LTRIM(pd.precinct, '0') = voters.precinct
            )
            LIMIT 1
        )
    WHERE congressional_district IS NULL
    AND EXISTS (
        SELECT 1 FROM precinct_districts pd
        WHERE pd.county = voters.county
        AND (
            pd.precinct = LTRIM(voters.precinct, '0')
            OR pd.precinct = voters.precinct
            OR LTRIM(pd.precinct, '0') = voters.precinct
        )
    )
""")

normalized = cursor.rowcount
log(f"✓ Updated {normalized:,} voters using normalized precinct match")

conn.commit()

# Check coverage
cursor.execute("SELECT COUNT(*) FROM voters WHERE congressional_district IS NOT NULL")
with_district = cursor.fetchone()[0]
coverage = 100 * with_district / total if total > 0 else 0

log(f"\n✓ District coverage: {with_district:,}/{total:,} ({coverage:.1f}%)")

# Verify D15
log("\n" + "="*80)
log("D15 ACCURACY CHECK")
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

# Show D15 county breakdown
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

for county, voters in cursor.fetchall():
    log(f"  {county:<20} {voters:>6,}")

conn.close()

log("\n" + "="*80)
log("COMPLETE!")
log("="*80)
