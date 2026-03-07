#!/usr/bin/env python3
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")

current = cursor.fetchone()[0]
target = 54573
diff = current - target

print(f"Current D15 Dem: {current:,}")
print(f"Target: {target:,}")
print(f"Difference: {diff:+,}")
print(f"Accuracy: {100 * (1 - abs(diff) / target):.2f}%")

conn.close()
