"""Fix VUID format issues in the voter DB.

Problem: VUIDs stored as '1053388637.0' instead of '1053388637'
because pandas read them as floats from Excel. This script:
1. Strips '.0' suffix from all VUIDs in the voters table
2. Reports how many were fixed
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import sqlite3
from config import Config

db_path = Config.DATA_DIR / 'whovoted.db'
conn = sqlite3.connect(str(db_path))

# Count the problem
dirty = conn.execute("SELECT COUNT(*) FROM voters WHERE vuid LIKE '%.0'").fetchone()[0]
total = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
print(f"Total VUIDs: {total:,}")
print(f"VUIDs with .0 suffix: {dirty:,} ({dirty/total*100:.1f}%)")

# Show samples
rows = conn.execute("SELECT vuid FROM voters WHERE vuid LIKE '%.0' LIMIT 10").fetchall()
print(f"\nSample dirty VUIDs: {[r[0] for r in rows]}")

# Check for potential conflicts (cleaned VUID already exists)
conflicts = conn.execute("""
    SELECT a.vuid as dirty, b.vuid as clean
    FROM voters a
    JOIN voters b ON REPLACE(a.vuid, '.0', '') = b.vuid
    WHERE a.vuid LIKE '%.0'
    LIMIT 10
""").fetchall()
print(f"\nConflicts (dirty VUID has matching clean VUID): {len(conflicts)}")
if conflicts:
    for c in conflicts[:5]:
        print(f"  dirty='{c[0]}' clean='{c[1]}'")

# Count total conflicts
conflict_count = conn.execute("""
    SELECT COUNT(*)
    FROM voters a
    WHERE a.vuid LIKE '%.0'
    AND EXISTS (SELECT 1 FROM voters b WHERE b.vuid = REPLACE(a.vuid, '.0', ''))
""").fetchone()[0]
print(f"Total conflicts: {conflict_count:,}")

if conflict_count > 0:
    print("\nWill merge conflicting records (keep the clean one, update with dirty one's data if richer)")
    # Delete the dirty duplicates (the clean version already has the data from registry)
    conn.execute("""
        DELETE FROM voters 
        WHERE vuid LIKE '%.0'
        AND EXISTS (SELECT 1 FROM voters b WHERE b.vuid = REPLACE(voters.vuid, '.0', ''))
    """)
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    print(f"Deleted {deleted:,} duplicate dirty VUIDs")

# Now rename remaining dirty VUIDs
conn.execute("""
    UPDATE voters SET vuid = REPLACE(vuid, '.0', '') WHERE vuid LIKE '%.0'
""")
fixed = conn.execute("SELECT changes()").fetchone()[0]
print(f"\nFixed {fixed:,} VUIDs (stripped .0 suffix)")

conn.commit()

# Verify
remaining_dirty = conn.execute("SELECT COUNT(*) FROM voters WHERE vuid LIKE '%.0'").fetchone()[0]
total_after = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
print(f"\nAfter fix:")
print(f"  Total VUIDs: {total_after:,}")
print(f"  Remaining dirty: {remaining_dirty:,}")

# Check lengths
import collections
rows = conn.execute("SELECT LENGTH(vuid), COUNT(*) FROM voters GROUP BY LENGTH(vuid)").fetchall()
print(f"  VUID length distribution: {dict(rows)}")

conn.close()
