#!/usr/bin/env python3
"""
Check geocoding quality in the cache and data files.
Shows how many addresses were geocoded at ZIP-code level vs street level.
"""

import json
import sys
from pathlib import Path
from collections import Counter

def check_cache_quality(cache_file):
    """Check quality of geocoded addresses in cache."""
    if not cache_file.exists():
        print(f"Cache file not found: {cache_file}")
        return
    
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    print(f"\n=== Geocoding Cache Quality Report ===")
    print(f"Total cached addresses: {len(cache)}")
    
    # Count by source
    sources = Counter()
    fallbacks = Counter()
    
    for address, result in cache.items():
        source = result.get('source', 'unknown')
        sources[source] += 1
        
        if result.get('fallback'):
            fallbacks[result['fallback']] += 1
    
    print(f"\nBy geocoding source:")
    for source, count in sources.most_common():
        pct = (count / len(cache)) * 100
        emoji = "✓" if source in ['census', 'photon'] else "→"
        print(f"  {emoji} {source}: {count} ({pct:.1f}%)")
    
    if fallbacks:
        print(f"\nFallback geocoding (LOW QUALITY):")
        for fallback, count in fallbacks.most_common():
            pct = (count / len(cache)) * 100
            print(f"  ⚠️  {fallback}: {count} ({pct:.1f}%)")
            print(f"      These addresses are geocoded to ZIP-code level only!")
    
    # Quality assessment
    zip_fallback_count = fallbacks.get('zip_code', 0)
    quality_pct = ((len(cache) - zip_fallback_count) / len(cache)) * 100
    
    print(f"\n=== Quality Score ===")
    print(f"Street-level accuracy: {quality_pct:.1f}%")
    
    if quality_pct < 80:
        print("⚠️  LOW QUALITY - Many addresses at ZIP-code level")
        print("   Recommendation: Clear cache and re-upload data")
        print("   Run: python scripts/clear_geocoding_cache.py")
    elif quality_pct < 95:
        print("⚠️  MODERATE QUALITY - Some ZIP-code fallbacks")
        print("   Recommendation: Consider clearing cache and re-uploading")
    else:
        print("✓ GOOD QUALITY - Most addresses at street level")
    
    # Show provider breakdown
    print(f"\n=== Provider Performance ===")
    aws_count = sources.get('aws_location', 0)
    census_count = sources.get('census', 0)
    photon_count = sources.get('photon', 0)
    nominatim_count = sources.get('nominatim', 0)
    bing_count = sources.get('bing', 0)
    
    if aws_count > 0:
        print(f"✓ AWS Location Service: {aws_count} addresses (excellent accuracy)")
    if census_count > 0:
        print(f"✓ Census Bureau: {census_count} addresses (excellent accuracy)")
    if photon_count > 0:
        print(f"✓ Photon: {photon_count} addresses (good accuracy)")
    if nominatim_count > 0:
        print(f"→ Nominatim: {nominatim_count} addresses (variable accuracy)")
    if bing_count > 0:
        print(f"✓ Bing Maps: {bing_count} addresses (excellent accuracy)")

def check_map_data_quality(data_dir):
    """Check quality of geocoded addresses in map data files."""
    map_files = list(data_dir.glob('map_data*.json'))
    
    if not map_files:
        print(f"\nNo map data files found in {data_dir}")
        return
    
    print(f"\n=== Map Data Files ===")
    
    for map_file in map_files:
        with open(map_file, 'r') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        
        # Count unique coordinates
        coords = set()
        for feature in features:
            coord = tuple(feature['geometry']['coordinates'])
            coords.add(coord)
        
        # Calculate clustering ratio
        clustering_ratio = len(features) / len(coords) if coords else 0
        
        print(f"\n{map_file.name}:")
        print(f"  Total addresses: {len(features)}")
        print(f"  Unique locations: {len(coords)}")
        print(f"  Clustering ratio: {clustering_ratio:.2f}")
        
        if clustering_ratio > 2:
            print(f"  ⚠️  HIGH CLUSTERING - Many addresses at same location")
        elif clustering_ratio > 1.5:
            print(f"  ⚠️  MODERATE CLUSTERING - Some duplicate locations")
        else:
            print(f"  ✓ LOW CLUSTERING - Good address spread")

def main():
    # Determine paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    cache_file = project_dir / 'data' / 'geocoding_cache.json'
    data_dir = project_dir / 'public' / 'data'
    
    print("WhoVoted Geocoding Quality Checker")
    print("=" * 50)
    
    # Check cache
    check_cache_quality(cache_file)
    
    # Check map data
    check_map_data_quality(data_dir)
    
    print("\n" + "=" * 50)
    print("\nFor detailed fix instructions, see:")
    print("  WhoVoted/GEOCODING_ACCURACY_FIX.md")

if __name__ == '__main__':
    main()
