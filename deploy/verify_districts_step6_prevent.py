#!/usr/bin/env python3
"""
STEP 6: PREVENT - Add safeguards to prevent future district assignment errors
Create validation checks that run automatically.
"""

import sqlite3
import json

def create_validation_checks():
    """Create SQL views and triggers for ongoing validation."""
    
    conn = sqlite3.connect('data/whovoted.db')
    
    print("=" * 80)
    print("CREATE VALIDATION SAFEGUARDS")
    print("=" * 80)
    
    print("\n" + "=" * 80)
    print("1. CREATE VALIDATION VIEWS")
    print("=" * 80)
    
    # View: Voters in wrong counties for their district
    print("\nCreating view: district_validation_errors...")
    conn.execute('''
        CREATE VIEW IF NOT EXISTS district_validation_errors AS
        SELECT 
            vuid,
            firstname,
            lastname,
            county,
            congressional_district,
            'Travis County in TX-15' as error_type
        FROM voters
        WHERE county = 'Travis' AND congressional_district = '15'
        
        UNION ALL
        
        SELECT 
            vuid,
            firstname,
            lastname,
            county,
            congressional_district,
            'Bexar County in TX-15' as error_type
        FROM voters
        WHERE county = 'Bexar' AND congressional_district = '15'
        
        UNION ALL
        
        SELECT 
            vuid,
            firstname,
            lastname,
            county,
            congressional_district,
            'Dallas County in TX-15' as error_type
        FROM voters
        WHERE county = 'Dallas' AND congressional_district = '15'
    ''')
    print("✓ Created district_validation_errors view")
    
    # View: Commissioner districts spanning multiple counties
    print("\nCreating view: multi_county_commissioner_districts...")
    conn.execute('''
        CREATE VIEW IF NOT EXISTS multi_county_commissioner_districts AS
        SELECT 
            commissioner_district,
            COUNT(DISTINCT county) as county_count,
            GROUP_CONCAT(DISTINCT county) as counties
        FROM voters
        WHERE commissioner_district IS NOT NULL AND commissioner_district != ''
        GROUP BY commissioner_district
        HAVING COUNT(DISTINCT county) > 1
    ''')
    print("✓ Created multi_county_commissioner_districts view")
    
    # View: Geocoded voters without district assignments
    print("\nCreating view: geocoded_without_districts...")
    conn.execute('''
        CREATE VIEW IF NOT EXISTS geocoded_without_districts AS
        SELECT 
            vuid,
            firstname,
            lastname,
            county,
            lat,
            lng,
            CASE 
                WHEN congressional_district IS NULL THEN 'Missing CD'
                ELSE NULL
            END as missing_cd,
            CASE 
                WHEN state_house_district IS NULL THEN 'Missing SH'
                ELSE NULL
            END as missing_sh
        FROM voters
        WHERE geocoded = 1 
        AND lat IS NOT NULL 
        AND lng IS NOT NULL
        AND (congressional_district IS NULL OR state_house_district IS NULL)
    ''')
    print("✓ Created geocoded_without_districts view")
    
    conn.commit()
    
    print("\n" + "=" * 80)
    print("2. CREATE VALIDATION FUNCTION")
    print("=" * 80)
    
    # Create a Python script that can be run regularly
    validation_script = '''#!/usr/bin/env python3
"""
Automated District Validation Check
Run this regularly to catch district assignment errors early.
"""

import sqlite3
import sys
from datetime import datetime

def main():
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print(f"District Validation Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    errors_found = False
    
    # Check 1: Known wrong assignments
    wrong_assignments = conn.execute('SELECT COUNT(*) as count FROM district_validation_errors').fetchone()
    if wrong_assignments['count'] > 0:
        print(f"✗ CRITICAL: {wrong_assignments['count']} voters in wrong districts")
        errors_found = True
    else:
        print("✓ No known wrong district assignments")
    
    # Check 2: Multi-county commissioner districts
    multi_county = conn.execute('SELECT COUNT(*) as count FROM multi_county_commissioner_districts').fetchone()
    if multi_county['count'] > 0:
        print(f"✗ CRITICAL: {multi_county['count']} commissioner districts span multiple counties")
        errors_found = True
    else:
        print("✓ No multi-county commissioner districts")
    
    # Check 3: Missing districts for geocoded voters
    missing = conn.execute('SELECT COUNT(*) as count FROM geocoded_without_districts').fetchone()
    if missing['count'] > 0:
        pct = conn.execute('''
            SELECT 
                COUNT(*) as total,
                (SELECT COUNT(*) FROM geocoded_without_districts) as missing
            FROM voters WHERE geocoded = 1
        ''').fetchone()
        missing_pct = pct['missing'] / pct['total'] * 100
        
        if missing_pct > 5:
            print(f"⚠️  WARNING: {missing['count']} geocoded voters missing districts ({missing_pct:.1f}%)")
        else:
            print(f"✓ Only {missing['count']} geocoded voters missing districts ({missing_pct:.1f}%)")
    else:
        print("✓ All geocoded voters have district assignments")
    
    conn.close()
    
    if errors_found:
        print("\\n✗ VALIDATION FAILED - Errors found")
        sys.exit(1)
    else:
        print("\\n✓ VALIDATION PASSED - All checks OK")
        sys.exit(0)

if __name__ == '__main__':
    main()
'''
    
    with open('deploy/validate_districts.py', 'w') as f:
        f.write(validation_script)
    
    print("✓ Created deploy/validate_districts.py")
    print("  Run this script regularly to check for errors")
    
    print("\n" + "=" * 80)
    print("3. CREATE MONITORING QUERIES")
    print("=" * 80)
    
    queries = {
        'check_tx15_composition.sql': '''
-- Verify TX-15 only has correct counties
SELECT 
    county,
    COUNT(*) as voter_count,
    CASE 
        WHEN county IN ('Hidalgo', 'Starr', 'Brooks', 'Jim Hogg', 'Willacy', 'Kenedy') 
        THEN 'CORRECT'
        ELSE 'WRONG'
    END as status
FROM voters
WHERE congressional_district = '15'
GROUP BY county
ORDER BY voter_count DESC;
''',
        'check_district_coverage.sql': '''
-- Check district assignment coverage
SELECT 
    'Congressional' as district_type,
    COUNT(*) as total_geocoded,
    COUNT(CASE WHEN congressional_district IS NOT NULL THEN 1 END) as with_district,
    ROUND(COUNT(CASE WHEN congressional_district IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as coverage_pct
FROM voters
WHERE geocoded = 1

UNION ALL

SELECT 
    'State House' as district_type,
    COUNT(*) as total_geocoded,
    COUNT(CASE WHEN state_house_district IS NOT NULL THEN 1 END) as with_district,
    ROUND(COUNT(CASE WHEN state_house_district IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as coverage_pct
FROM voters
WHERE geocoded = 1;
'''
    }
    
    for filename, query in queries.items():
        with open(f'deploy/{filename}', 'w') as f:
            f.write(query)
        print(f"✓ Created deploy/{filename}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    
    print("\n✓ Validation safeguards created")
    print("\nRegular maintenance:")
    print("  1. Run: python3 deploy/validate_districts.py (daily)")
    print("  2. Check views for errors before major releases")
    print("  3. Re-run district rebuild if boundaries change")

def main():
    create_validation_checks()
    
    print("\n" + "=" * 80)
    print("DISTRICT ACCURACY FIX - COMPLETE")
    print("=" * 80)
    
    print("\nAll steps completed:")
    print("  ✓ Step 1: Diagnosed the problem")
    print("  ✓ Step 2: Acquired official boundaries")
    print("  ✓ Step 3: Validated assignment logic")
    print("  ✓ Step 4: Rebuilt all assignments")
    print("  ✓ Step 5: Verified corrections")
    print("  ✓ Step 6: Added prevention safeguards")
    
    print("\nFinal steps:")
    print("  1. Regenerate cached reports: python3 deploy/regenerate_district_cache_complete.py")
    print("  2. Test campaign reports to verify accuracy")
    print("  3. Deploy to production")

if __name__ == '__main__':
    main()
