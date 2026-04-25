#!/usr/bin/env python3
"""Verify all claim numbers for the bond analysis writeup."""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
ZIPS = ('78501','78502','78503','78504','78505')
ELECTION = '2026-05-10'

conn = sqlite3.connect(DB)
ph = ','.join('?' * len(ZIPS))

# Age group turnout
print("=== AGE GROUP TURNOUT ===")
rows = conn.execute(f"""
SELECT
  CASE
    WHEN (2026 - v.birth_year) BETWEEN 18 AND 25 THEN '18-25'
    WHEN (2026 - v.birth_year) BETWEEN 26 AND 35 THEN '26-35'
    WHEN (2026 - v.birth_year) BETWEEN 36 AND 45 THEN '36-45'
    WHEN (2026 - v.birth_year) BETWEEN 46 AND 55 THEN '46-55'
    WHEN (2026 - v.birth_year) BETWEEN 56 AND 65 THEN '56-65'
    WHEN (2026 - v.birth_year) > 65 THEN '65+'
    ELSE 'Unk'
  END as ag,
  SUM(CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END) as voted,
  COUNT(*) as reg
FROM voters v
LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
GROUP BY ag ORDER BY ag
""", (ELECTION,) + ZIPS).fetchall()
for r in rows:
    pct = r[1]/r[2]*100 if r[2] else 0
    print(f"  {r[0]}: {r[1]:,} voted / {r[2]:,} reg = {pct:.2f}%")

# Regular voters (3+ past elections) who skipped this bond
print("\n=== REGULAR VOTERS WHO SKIPPED ===")
rv = conn.execute(f"""
SELECT COUNT(*) FROM (
  SELECT v.vuid, COUNT(ve2.election_date) as past
  FROM voters v
  INNER JOIN voter_elections ve2 ON v.vuid = ve2.vuid AND ve2.election_date != ?
  WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
  GROUP BY v.vuid HAVING past >= 3
) sub
WHERE sub.vuid NOT IN (
  SELECT vuid FROM voter_elections WHERE election_date = ?
)
""", (ELECTION,) + ZIPS + (ELECTION,)).fetchone()
print(f"  Regular voters (3+ past elections) who skipped bond: {rv[0]:,}")

# Total voted
tv = conn.execute(f"""
SELECT COUNT(DISTINCT v.vuid)
FROM voters v
INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
""", (ELECTION,) + ZIPS).fetchone()
print(f"\n  Total McAllen voters: {tv[0]:,}")

conn.close()
