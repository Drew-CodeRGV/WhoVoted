"""Batch geocode ungeocoded voter addresses from the registry DB.

Runs as a background process on the server. Processes addresses in batches,
updates the voter DB with coordinates, and saves to the geocoding cache.

Usage: python geocode_registry.py [--county Hidalgo] [--batch-size 100] [--max-workers 10]
"""
import sys
import gc
import json
import time
import argparse
import logging
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/opt/whovoted/backend')

from config import Config, setup_logging
from geocoder import GeocodingCache, NominatimGeocoder
import database as db

logger = setup_logging()

STATUS_FILE = Config.DATA_DIR / 'geocode_registry_status.json'


def write_status(status: dict):
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write status: {e}")


def geocode_registry(county='Hidalgo', batch_size=100, max_workers=10):
    """Geocode all ungeocoded voter addresses for a county."""
    db.init_db()
    
    # Initialize geocoder
    cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
    geocoder = NominatimGeocoder(cache)
    
    conn = db.get_connection()
    
    # Get total ungeocoded count
    total_ungeocoded = conn.execute(
        "SELECT COUNT(*) FROM voters WHERE geocoded = 0 AND address != '' AND county = ?",
        (county,)
    ).fetchone()[0]
    
    total_geocoded_start = conn.execute(
        "SELECT COUNT(*) FROM voters WHERE geocoded = 1 AND county = ?",
        (county,)
    ).fetchone()[0]
    
    print(f"County: {county}")
    print(f"Already geocoded: {total_geocoded_start:,}")
    print(f"Need geocoding: {total_ungeocoded:,}")
    print(f"Batch size: {batch_size}, Workers: {max_workers}")
    print()
    
    status = {
        'running': True,
        'county': county,
        'total_to_geocode': total_ungeocoded,
        'processed': 0,
        'geocoded': 0,
        'failed': 0,
        'cache_hits': 0,
        'started_at': datetime.now().isoformat(),
        'last_update': datetime.now().isoformat()
    }
    write_status(status)
    
    processed = 0
    geocoded = 0
    failed = 0
    cache_hits = 0
    start_time = time.time()
    
    while True:
        # Fetch a batch of ungeocoded voters
        rows = conn.execute("""
            SELECT vuid, address FROM voters 
            WHERE geocoded = 0 AND address != '' AND address IS NOT NULL AND county = ?
            LIMIT ?
        """, (county, batch_size)).fetchall()
        
        if not rows:
            break
        
        # Deduplicate addresses in this batch
        addr_to_vuids = {}
        for vuid, address in rows:
            addr_key = address.strip().upper()
            if addr_key not in addr_to_vuids:
                addr_to_vuids[addr_key] = []
            addr_to_vuids[addr_key].append(vuid)
        
        # Geocode unique addresses in parallel
        results = {}  # address -> (lat, lng, display_name) or None
        
        def geocode_one(address):
            try:
                result = geocoder.geocode(address)
                return address, result
            except Exception as e:
                logger.warning(f"Geocode error for {address}: {e}")
                return address, None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(geocode_one, addr): addr for addr in addr_to_vuids.keys()}
            for future in as_completed(futures):
                addr, result = future.result()
                results[addr] = result
        
        # Update DB with results
        now = datetime.now().isoformat()
        for addr, result in results.items():
            vuids = addr_to_vuids[addr]
            if result and result.get('lat') and result.get('lng'):
                lat = result['lat']
                lng = result['lng']
                display_name = result.get('display_name', '')
                
                # Update all voters with this address
                placeholders = ','.join('?' * len(vuids))
                conn.execute(
                    f"UPDATE voters SET lat = ?, lng = ?, geocoded = 1, updated_at = ? WHERE vuid IN ({placeholders})",
                    [lat, lng, now] + vuids
                )
                geocoded += len(vuids)
                
                # Also save to geocoding cache in DB
                conn.execute("""
                    INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(address_key) DO UPDATE SET
                        lat = excluded.lat, lng = excluded.lng,
                        display_name = excluded.display_name
                """, (addr, lat, lng, display_name, 'batch_geocode', now))
            else:
                # Mark as attempted but failed (set geocoded = -1 to skip next time)
                placeholders = ','.join('?' * len(vuids))
                conn.execute(
                    f"UPDATE voters SET geocoded = -1, updated_at = ? WHERE vuid IN ({placeholders})",
                    [now] + vuids
                )
                failed += len(vuids)
        
        conn.commit()
        processed += len(rows)
        
        # Update status
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (total_ungeocoded - processed) / rate if rate > 0 else 0
        
        stats = geocoder.get_stats()
        cache_hits = stats.get('cache_hits', 0)
        
        status.update({
            'processed': processed,
            'geocoded': geocoded,
            'failed': failed,
            'cache_hits': cache_hits,
            'rate': round(rate, 1),
            'elapsed_seconds': round(elapsed),
            'estimated_remaining_seconds': round(remaining),
            'last_update': datetime.now().isoformat()
        })
        write_status(status)
        
        print(f"  Processed: {processed:,}/{total_ungeocoded:,} | "
              f"Geocoded: {geocoded:,} | Failed: {failed:,} | "
              f"Rate: {rate:.1f}/s | ETA: {remaining/60:.0f}m")
        
        # Brief pause to avoid hammering APIs
        time.sleep(0.1)
    
    # Final status
    elapsed = time.time() - start_time
    status.update({
        'running': False,
        'processed': processed,
        'geocoded': geocoded,
        'failed': failed,
        'elapsed_seconds': round(elapsed),
        'completed_at': datetime.now().isoformat()
    })
    write_status(status)
    
    # Save geocoder cache to disk
    cache.save_cache()
    
    print(f"\n{'='*50}")
    print(f"GEOCODING COMPLETE")
    print(f"{'='*50}")
    print(f"Processed: {processed:,}")
    print(f"Geocoded:  {geocoded:,}")
    print(f"Failed:    {failed:,}")
    print(f"Time:      {elapsed:.0f}s ({elapsed/60:.1f}m)")
    
    # Print final DB stats
    total = conn.execute("SELECT COUNT(*) FROM voters WHERE county = ?", (county,)).fetchone()[0]
    geo = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1 AND county = ?", (county,)).fetchone()[0]
    print(f"\nDB: {geo:,}/{total:,} geocoded ({geo/total*100:.1f}%)")

    # Rebuild static cache files so the API serves fresh data instantly
    if geocoded > 0:
        print("\nRebuilding static cache files...")
        try:
            import subprocess
            result = subprocess.run(
                ['/opt/whovoted/venv/bin/python3', '/opt/whovoted/deploy/optimize_performance.py'],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode == 0:
                print("Performance optimization completed successfully.")
            else:
                print(f"Optimization failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"Optimization error: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--county', default='Hidalgo')
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--max-workers', type=int, default=10)
    args = parser.parse_args()
    
    geocode_registry(args.county, args.batch_size, args.max_workers)
