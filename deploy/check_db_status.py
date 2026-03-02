#!/usr/bin/env python3
"""Quick script to check database status and district columns."""

import sqlite3
import sys

def check_database():
    try:
        conn = sqlite3.connect('/opt/whovoted/data/voters.db', timeout=5)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute('PRAGMA table_info(voters)')
        columns = [row[1] for row in cursor.fetchall()]
        
        district_cols = [c for c in columns if 'district' in c.lower()]
        print(f"District columns found: {district_cols}")
        
        if district_cols:
            # Check if columns have data
            for col in district_cols:
                cursor.execute(f'SELECT COUNT(*) FROM voters WHERE {col} IS NOT NULL')
                count = cursor.fetchone()[0]
                print(f"  {col}: {count:,} rows with data")
        
        # Check total voters
        cursor.execute('SELECT COUNT(*) FROM voters')
        total = cursor.fetchone()[0]
        print(f"\nTotal voters: {total:,}")
        
        conn.close()
        print("\nDatabase is accessible and not locked.")
        return True
        
    except sqlite3.OperationalError as e:
        print(f"ERROR: Database is locked or inaccessible: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == '__main__':
    success = check_database()
    sys.exit(0 if success else 1)
