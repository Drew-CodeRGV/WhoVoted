#!/usr/bin/env python3
"""Count unique addresses among ungeocoded voters to estimate geocoding work."""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)

# Total ungeocoded
r = conn.execute("""
    SELECT COUNT(*) FROM voters 
    WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL) 
    AND address IS NOT NULL AND address != ''
""").fetchone()
print(f"Total ungeocoded voters with addresses: {r[0]:,}")

# Unique addresses among ungeocoded
r2 = conn.execute("""
    SELECT COUNT(DISTINCT UPPER(TRIM(address || ', ' || COALESCE(city,'') || ', TX ' || COALESCE(zip,'')))) 
    FROM voters 
    WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL) 
    AND address IS NOT NULL AND address != ''
""").fetchone()
print(f"Unique addresses to geocode: {r2[0]:,}")

# How many of those unique addresses are already in the cache?
# First get the unique addresses
rows = conn.execute("""
    SELECT DISTINCT UPPER(TRIM(address)) as addr
    FROM voters 
    WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL) 
    AND address IS NOT NULL AND address != ''
""").fetchall()
unique_addrs = set(r[0] for r in rows)
print(f"Unique raw addresses: {len(unique_addrs):,}")

# Check cache coverage
cache_rows = conn.execute("SELECT address_key FROM geocoding_cache").fetchall()
cache_keys = set(r[0] for r in cache_rows)
print(f"Cache entries: {len(cache_keys):,}")

# Check overlap
hits = 0
for addr in unique_addrs:
    if addr in cache_keys or addr.upper() in cache_keys:
        hits += 1
print(f"Cache hits (exact match): {hits:,}")

# Also check how many geocoded voters share addresses with ungeocoded ones
r3 = conn.execute("""
    SELECT COUNT(DISTINCT UPPER(TRIM(address))) 
    FROM voters 
    WHERE county='Hidalgo' AND geocoded=1
""").fetchone()
print(f"\nUnique addresses among geocoded voters: {r3[0]:,}")

# Check if geocoded voter addresses overlap with ungeocoded
geocoded_addrs = conn.execute("""
    SELECT DISTINCT UPPER(TRIM(address)) as addr, lat, lng
    FROM voters 
    WHERE county='Hidalgo' AND geocoded=1 AND lat IS NOT NULL AND lng IS NOT NULL
""").fetchall()
geocoded_map = {r[0]: (r[1], r[2]) for r in geocoded_addrs}
print(f"Unique geocoded addresses with coords: {len(geocoded_map):,}")

overlap = 0
for addr in unique_addrs:
    if addr in geocoded_map:
        overlap += 1
print(f"Ungeocoded addresses that match a geocoded voter's address: {overlap:,}")
print(f"Addresses that truly need AWS geocoding: {len(unique_addrs) - overlap - hits:,}")

conn.close()
