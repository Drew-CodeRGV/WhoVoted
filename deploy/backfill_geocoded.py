"""Backfill voter DB with geocoded coordinates from existing map_data files,
and migrate the JSON geocoding cache into SQLite.

This script:
1. Scans all map_data_*.json files for VUIDs with coordinates
2. Updates matching voter records in the DB with lat/lng
3. Migrates geocoded_addresses.json into the geocoding_cache table
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/whovoted/backend')
from config import Config
import database as db

def backfill_voter_coords():
    """Pull geocoded coords from map_data GeoJSON files into the voter DB."""
    data_dir = Config.PUBLIC_DIR / 'data'
    
    # Collect all unique VUIDs with coordinates (keep most recent)
    geocoded_vuids = {}  # vuid -> (lat, lng)
    
    for f in sorted(data_dir.glob('map_data_*.json')):
        try:
            with open(f, 'r') as fh:
                geojson = json.load(fh)
            count = 0
            for feature in geojson.get('features', []):
                props = feature.get('properties', {})
                geom = feature.get('geometry')
                if not geom:
                    continue
                coords = geom.get('coordinates', [])
                vuid = str(props.get('vuid', '')).strip()
                if not vuid:
                    vuid = str(props.get('cert', '')).strip()
                # Strip .0 suffix from float-converted VUIDs
                if vuid.endswith('.0'):
                    vuid = vuid[:-2]
                if vuid and len(coords) >= 2:
                    lng, lat = float(coords[0]), float(coords[1])
                    if lat != 0 and lng != 0:
                        geocoded_vuids[vuid] = (lat, lng)
                        count += 1
            print(f"  {f.name}: {count} VUIDs")
        except Exception as e:
            print(f"  {f.name}: ERROR {e}")
    
    print(f"\nTotal unique geocoded VUIDs: {len(geocoded_vuids):,}")
    
    # Update voter DB in batches
    conn = db.get_connection()
    updated = 0
    batch_size = 500
    items = list(geocoded_vuids.items())
    now = datetime.now().isoformat()
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for vuid, (lat, lng) in batch:
            cursor = conn.execute(
                "UPDATE voters SET lat = ?, lng = ?, geocoded = 1, updated_at = ? WHERE vuid = ? AND geocoded = 0",
                (lat, lng, now, vuid)
            )
            updated += cursor.rowcount
        conn.commit()
        if (i + batch_size) % 5000 == 0 or i + batch_size >= len(items):
            print(f"  Progress: {min(i + batch_size, len(items)):,} / {len(items):,} checked, {updated:,} updated")
    
    print(f"\nBackfill complete: {updated:,} voter records updated with coordinates")
    return updated


def migrate_json_cache():
    """Migrate geocoded_addresses.json into SQLite geocoding_cache table."""
    cache_path = Config.DATA_DIR / 'geocoded_addresses.json'
    if not cache_path.exists():
        print("No JSON geocoding cache found, skipping")
        return 0
    
    with open(cache_path, 'r') as f:
        cache_data = json.load(f)
    
    print(f"JSON cache has {len(cache_data):,} entries")
    
    conn = db.get_connection()
    migrated = 0
    now = datetime.now().isoformat()
    batch = []
    
    for address_key, entry in cache_data.items():
        if isinstance(entry, dict):
            lat = entry.get('lat')
            lng = entry.get('lng')
            display_name = entry.get('display_name', '')
        elif isinstance(entry, list) and len(entry) >= 2:
            lat, lng = entry[0], entry[1]
            display_name = ''
        else:
            continue
        
        if lat is not None and lng is not None:
            batch.append((address_key, lat, lng, display_name, 'migrated', now))
            migrated += 1
        
        if len(batch) >= 500:
            conn.executemany("""
                INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(address_key) DO UPDATE SET
                    lat = excluded.lat, lng = excluded.lng,
                    display_name = excluded.display_name,
                    source = excluded.source, cached_at = excluded.cached_at
            """, batch)
            conn.commit()
            batch = []
    
    if batch:
        conn.executemany("""
            INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(address_key) DO UPDATE SET
                lat = excluded.lat, lng = excluded.lng,
                display_name = excluded.display_name,
                source = excluded.source, cached_at = excluded.cached_at
        """, batch)
        conn.commit()
    
    print(f"Migrated {migrated:,} cache entries to SQLite")
    return migrated


def print_summary():
    """Print final DB stats."""
    conn = db.get_connection()
    total = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
    geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1").fetchone()[0]
    cache_count = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
    pct = (geocoded / total * 100) if total > 0 else 0
    
    print(f"\n{'='*50}")
    print(f"FINAL DATABASE STATE")
    print(f"{'='*50}")
    print(f"Total voters:     {total:,}")
    print(f"Geocoded:         {geocoded:,} ({pct:.1f}%)")
    print(f"Need geocoding:   {total - geocoded:,} ({100-pct:.1f}%)")
    print(f"Geocoding cache:  {cache_count:,} addresses")
    print(f"{'='*50}")


if __name__ == '__main__':
    db.init_db()
    
    print("=" * 50)
    print("STEP 1: Backfill voter coords from map_data files")
    print("=" * 50)
    backfill_voter_coords()
    
    print()
    print("=" * 50)
    print("STEP 2: Migrate JSON geocoding cache to SQLite")
    print("=" * 50)
    migrate_json_cache()
    
    print_summary()
