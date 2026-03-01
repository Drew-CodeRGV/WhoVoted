#!/usr/bin/env python3
"""Check geocoding status for Hidalgo County voters."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Overall counts
row = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN geocoded=1 THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN geocoded=0 AND address IS NOT NULL AND address != '' THEN 1 ELSE 0 END) as ungeocoded_with_addr,
        SUM(CASE WHEN address IS NULL OR address = '' THEN 1 ELSE 0 END) as no_address
    FROM voters WHERE county='Hidalgo'
""").fetchone()

print(f"Hidalgo County Voters:")
print(f"  Total: {row['total']:,}")
print(f"  Geocoded: {row['geocoded']:,}")
print(f"  Ungeocoded (with address): {row['ungeocoded_with_addr']:,}")
print(f"  No address: {row['no_address']:,}")
print(f"  Geocode rate: {row['geocoded']/row['total']*100:.1f}%")

# Check unique addresses to geocode
row2 = conn.execute("""
    SELECT COUNT(DISTINCT address) as unique_addrs
    FROM voters 
    WHERE county='Hidalgo' AND geocoded=0 AND address IS NOT NULL AND address != ''
""").fetchone()
print(f"\n  Unique ungeocoded addresses: {row2['unique_addrs']:,}")

conn.close()
