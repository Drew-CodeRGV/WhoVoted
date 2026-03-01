"""Check how many ungeocoded voter addresses can be resolved from the geocoding cache."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import sqlite3
from config import Config

db_path = Config.DATA_DIR / 'whovoted.db'
conn = sqlite3.connect(str(db_path))

# Get all ungeocoded voter addresses
print("Fetching ungeocoded voter addresses...")
rows = conn.execute(
    "SELECT vuid, address FROM voters WHERE geocoded = 0 AND address != '' AND address IS NOT NULL"
).fetchall()
print(f"Ungeocoded voters with addresses: {len(rows):,}")

# Get all cached addresses
print("Loading geocoding cache...")
cache_rows = conn.execute("SELECT address_key, lat, lng FROM geocoding_cache").fetchall()
cache = {r[0]: (r[1], r[2]) for r in cache_rows}
print(f"Cache entries: {len(cache):,}")

# Check how many addresses match cache (exact match on address string)
matched = 0
unmatched = 0
sample_unmatched = []

for vuid, address in rows:
    addr_upper = address.strip().upper() if address else ''
    if addr_upper in cache:
        matched += 1
    else:
        unmatched += 1
        if len(sample_unmatched) < 10:
            sample_unmatched.append(address)

print(f"\nCache coverage for ungeocoded voters:")
print(f"  Matched in cache: {matched:,} ({matched/len(rows)*100:.1f}%)")
print(f"  Not in cache: {unmatched:,} ({unmatched/len(rows)*100:.1f}%)")

# Check unique addresses
unique_addrs = set()
for vuid, address in rows:
    if address:
        unique_addrs.add(address.strip().upper())
print(f"\nUnique ungeocoded addresses: {len(unique_addrs):,}")

# How many unique addresses are in cache
cached_unique = sum(1 for a in unique_addrs if a in cache)
print(f"Unique addresses in cache: {cached_unique:,}")
print(f"Unique addresses needing geocoding: {len(unique_addrs) - cached_unique:,}")

print(f"\nSample unmatched addresses:")
for a in sample_unmatched[:10]:
    print(f"  {a}")

conn.close()
