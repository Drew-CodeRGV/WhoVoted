#!/usr/bin/env python3
"""Fix voters with NULL/empty county by checking their voter_elections source_file."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db
db.init_db()

conn = db.get_connection()

# Find voters with no county
rows = conn.execute("SELECT COUNT(*) FROM voters WHERE county IS NULL OR county = ''").fetchone()
print(f"Voters with no county: {rows[0]}")

# Update based on source_file patterns
updated = conn.execute("""
    UPDATE voters SET county = 'Brooks'
    WHERE (county IS NULL OR county = '')
    AND vuid IN (
        SELECT DISTINCT vuid FROM voter_elections
        WHERE source_file LIKE '%Voting_History%'
    )
""").rowcount
conn.commit()
print(f"Updated {updated} voters to Brooks county")

# Check remaining
rows = conn.execute("SELECT COUNT(*) FROM voters WHERE county IS NULL OR county = ''").fetchone()
print(f"Remaining voters with no county: {rows[0]}")
