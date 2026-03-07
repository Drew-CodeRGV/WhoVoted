#!/usr/bin/env python3
"""
Use the pre-parsed JSON precinct data which has complete mappings
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data/district_reference')
ELECTION_DATE = '2026-03-03'
TARGET_D15 = 54573

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def normalize_precinct(p):
    """Normalize precinct for matching"""
    if not p:
        return None
    # Remove ** prefix and spaces
    p = str(p).replace('**', '').replace('*', '').strip().upper()
    return p if p else None

def normalize_county(c):
    """Normalize county name"""
    if not c:
        return None
    # Remove * suffix and spaces
    c = str(c).replace('*', '').strip().title()
    c = c.replace('Mclennan', 'McLennan')
    c = c.replace('Lasalle', 'La Salle')
    c = c.replace('Dewitt', 'DeWitt')
    return c

log("="*80)
log("REBUILD PRECINCT_DISTRICTS FROM JSON")
log("="*80)

conn = sqlite3.connect(DB_PATH, timeout=120.0)
conn.execute('PRAGMA journal_mode=WAL')
cursor = conn.cursor()

# Clear and rebuild table
log("\nClearing precinct_districts table...")
cursor.execute("DELETE FROM precinct_districts")
conn.commit()

# Load JSON files - focus on congressional for now
files = {
    'congressional': DATA_DIR / 'congressional_precincts.json',
}

all_mappings = {}

for district_type, file_path in files.items():
    if not file_path.exists():
        log(f"File not found: {file_path}")
        continue
    
    log(f"\nLoading {file_path.name}...")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    count = 0
    
    # Handle different JSON structures
    if 'by_county' in str(data)[:1000]:  # Precinct-level data
        for district, district_data in data.items():
            if isinstance(district_data, dict) and 'by_county' in district_data:
                for county, precincts in district_data['by_county'].items():
                    county_norm = normalize_county(county)
                    if not county_norm:
                        continue
                    
                    if isinstance(precincts, list):
                        for precinct in precincts:
                            precinct_norm = normalize_precinct(precinct)
                            if not precinct_norm:
                                continue
                            
                            key = (county_norm, precinct_norm)
                            if key not in all_mappings:
                                all_mappings[key] = {}
                            all_mappings[key][district_type] = district
                            count += 1
    
    log(f"  Loaded {count:,} precinct mappings")

# Insert into database
log(f"\nInserting {len(all_mappings):,} mappings into database...")

for (county, precinct), districts in all_mappings.items():
    cursor.execute("""
        INSERT OR REPLACE INTO precinct_districts (county, precinct, congressional_district, state_senate_district, state_house_district)
        VALUES (?, ?, ?, ?, ?)
    """, (
        county,
        precinct,
        districts.get('congressional'),
        districts.get('senate'),
        districts.get('house')
    ))

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM precinct_districts")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT county) FROM precinct_districts")
counties = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT congressional_district) FROM precinct_districts WHERE congressional_district IS NOT NULL")
cong_districts = cursor.fetchone()[0]

log(f"\n✓ Complete!")
log(f"  Total mappings: {total:,}")
log(f"  Counties: {counties}")
log(f"  Congressional districts: {cong_districts}")

# Now reassign all voters
log("\n" + "="*80)
log("REASSIGNING ALL VOTERS")
log("="*80)

# Clear existing assignments
log("\nClearing existing assignments...")
cursor.execute("UPDATE voters SET congressional_district = NULL, state_senate_district = NULL, state_house_district = NULL")
conn.commit()

# Reassign with flexible matching
strategies = [
    ("Exact match", "pd.precinct = voters.precinct"),
    ("Strip zeros", "LTRIM(pd.precinct, '0') = LTRIM(voters.precinct, '0')"),
    ("Pad to 4", "pd.precinct = SUBSTR('0000' || LTRIM(voters.precinct, '0'), -4)"),
]

total_updated = 0
for strategy_name, condition in strategies:
    log(f"\n  {strategy_name}...")
    cursor.execute(f"""
        UPDATE voters
        SET congressional_district = (
            SELECT pd.congressional_district
            FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND {condition}
            LIMIT 1
        )
        WHERE congressional_district IS NULL
        AND voters.precinct IS NOT NULL
        AND voters.precinct != ''
        AND EXISTS (
            SELECT 1 FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND {condition}
        )
    """)
    updated = cursor.rowcount
    total_updated += updated
    log(f"    ✓ {updated:,} voters")
    conn.commit()

log(f"\n  Total: {total_updated:,} voters assigned")

# Check D15
log("\n" + "="*80)
log("D15 VERIFICATION")
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

if accuracy >= 99.0:
    log("  ✓ SUCCESS!")
else:
    log("  ⚠ Needs refinement")

conn.close()

log("\n" + "="*80)
log("COMPLETE!")
log("="*80)
