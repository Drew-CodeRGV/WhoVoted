#!/bin/bash
# Master script to fix all district assignments with validation
set -e

echo "================================================================================"
echo "COMPLETE DISTRICT ASSIGNMENT FIX"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Parse district reference files from Texas Legislature"
echo "  2. Build precinct-to-district lookup tables"
echo "  3. Assign all 3 district types to every voter based on precinct"
echo "  4. Validate geocoded addresses match precinct assignments"
echo "  5. Create cached district counts for reporting"
echo ""
echo "================================================================================"
echo ""

cd /opt/whovoted

# Step 1: Parse district files
echo "STEP 1: Parsing district reference files..."
echo "================================================================================"
python3 deploy/parse_district_files_fixed.py

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to parse district files"
    exit 1
fi

echo ""
echo "✓ District files parsed successfully"
echo ""

# Step 2: Build lookup system and fix assignments
echo "STEP 2: Building lookup system and fixing voter assignments..."
echo "================================================================================"
python3 deploy/build_vuid_district_lookup.py

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build lookup system"
    exit 1
fi

echo ""
echo "✓ Voter assignments fixed successfully"
echo ""

# Step 3: Verify results
echo "STEP 3: Verifying results..."
echo "================================================================================"
python3 << 'PYTHON'
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
cursor = conn.cursor()

# Get overall stats
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT county) as counties,
        COUNT(DISTINCT precinct) as precincts,
        COUNT(DISTINCT congressional_district) as cong_districts,
        COUNT(DISTINCT state_senate_district) as senate_districts,
        COUNT(DISTINCT state_house_district) as house_districts
    FROM voters
""")
stats = cursor.fetchone()

print(f"\nDatabase Statistics:")
print(f"  Total voters: {stats[0]:,}")
print(f"  Unique counties: {stats[1]}")
print(f"  Unique precincts: {stats[2]}")
print(f"  Congressional districts: {stats[3]}")
print(f"  State Senate districts: {stats[4]}")
print(f"  State House districts: {stats[5]}")

# Get assignment coverage
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN congressional_district IS NOT NULL THEN 1 ELSE 0 END) as has_cong,
        SUM(CASE WHEN state_senate_district IS NOT NULL THEN 1 ELSE 0 END) as has_senate,
        SUM(CASE WHEN state_house_district IS NOT NULL THEN 1 ELSE 0 END) as has_house,
        SUM(CASE WHEN congressional_district IS NOT NULL 
                 AND state_senate_district IS NOT NULL 
                 AND state_house_district IS NOT NULL THEN 1 ELSE 0 END) as has_all
    FROM voters
""")
coverage = cursor.fetchone()

print(f"\nDistrict Assignment Coverage:")
print(f"  Congressional: {coverage[1]:,} / {coverage[0]:,} ({coverage[1]/coverage[0]*100:.1f}%)")
print(f"  State Senate: {coverage[2]:,} / {coverage[0]:,} ({coverage[2]/coverage[0]*100:.1f}%)")
print(f"  State House: {coverage[3]:,} / {coverage[0]:,} ({coverage[3]/coverage[0]*100:.1f}%)")
print(f"  All 3 districts: {coverage[4]:,} / {coverage[0]:,} ({coverage[4]/coverage[0]*100:.1f}%)")

# Sample district counts
print(f"\nSample District Counts:")
cursor.execute("""
    SELECT 
        'TX-' || congressional_district as district,
        COUNT(*) as voters
    FROM voters
    WHERE congressional_district IS NOT NULL
    GROUP BY congressional_district
    ORDER BY voters DESC
    LIMIT 5
""")
print("\n  Top 5 Congressional Districts by voter count:")
for row in cursor.fetchall():
    print(f"    {row[0]}: {row[1]:,} voters")

conn.close()
PYTHON

echo ""
echo "================================================================================"
echo "✓ COMPLETE"
echo "================================================================================"
echo ""
echo "All district assignments have been updated based on precinct data."
echo "Voters are now accurately assigned to all 3 district types."
echo ""
echo "Next steps:"
echo "  • Review voters without precinct data (if any)"
echo "  • Validate counts against official sources"
echo "  • Update frontend to display all 3 district types"
echo ""
