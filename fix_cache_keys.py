"""Fix cache keys to use consistent TEXAS format."""
import json
import re
from pathlib import Path

cache_file = Path('data/geocoding_cache.json')
backup_file = Path('data/geocoding_cache_backup.json')

print("Loading cache...")
with open(cache_file, 'r') as f:
    old_cache = json.load(f)

print(f"Original cache size: {len(old_cache)} entries")

# Backup original cache
print("Creating backup...")
with open(backup_file, 'w') as f:
    json.dump(old_cache, f, indent=2)

def normalize_key(key):
    """Normalize cache key to use TEXAS instead of TX."""
    # Replace TX with TEXAS using word boundary
    normalized = re.sub(r'\bTX\b', 'TEXAS', key)
    return normalized

# Rebuild cache with normalized keys
new_cache = {}
duplicates = 0
tx_converted = 0

for old_key, value in old_cache.items():
    new_key = normalize_key(old_key)
    
    if old_key != new_key:
        tx_converted += 1
    
    if new_key in new_cache:
        # Key already exists - keep the one with better source
        existing_source = new_cache[new_key].get('source', 'unknown')
        new_source = value.get('source', 'unknown')
        
        # Priority: aws_location > census > photon > nominatim > unknown
        source_priority = {
            'aws_location': 5,
            'census': 4,
            'photon': 3,
            'nominatim': 2,
            'unknown': 1
        }
        
        if source_priority.get(new_source, 0) > source_priority.get(existing_source, 0):
            new_cache[new_key] = value
            duplicates += 1
    else:
        new_cache[new_key] = value

print(f"\nConverted {tx_converted} keys from TX to TEXAS format")
print(f"Resolved {duplicates} duplicate keys")
print(f"New cache size: {len(new_cache)} entries")

# Save normalized cache
print("\nSaving normalized cache...")
with open(cache_file, 'w') as f:
    json.dump(new_cache, f, indent=2)

print("Done! Cache has been normalized.")
print(f"Backup saved to: {backup_file}")
