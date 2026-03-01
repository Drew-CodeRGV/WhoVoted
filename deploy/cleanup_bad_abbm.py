#!/usr/bin/env python3
"""Clean up incorrectly processed ABBM records (Certificate used as VUID)."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

# Delete mail-in voter_elections records (they have wrong VUIDs from Certificate column)
deleted = conn.execute("DELETE FROM voter_elections WHERE voting_method = 'mail-in'")
print(f"Deleted {deleted.rowcount} mail-in voter_elections records")

# Also clean up any voters that were upserted with wrong VUIDs
# These would be short numeric VUIDs from the Certificate column
# Real Hidalgo VUIDs are 10 digits
deleted2 = conn.execute("""
    DELETE FROM voters 
    WHERE source = 'early-vote-upload' 
      AND LENGTH(vuid) < 8
      AND county = 'Hidalgo'
""")
print(f"Deleted {deleted2.rowcount} voters with short VUIDs (from Certificate column)")

conn.commit()
conn.close()
print("Done. Ready for reprocessing with correct VUID column.")
