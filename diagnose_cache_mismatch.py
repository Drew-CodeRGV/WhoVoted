"""Diagnose why cache isn't matching."""
import sys
import json
import pandas as pd
sys.path.insert(0, 'backend')

from processor import ProcessingJob
from geocoder import GeocodingCache
from config import Config

# Load cache
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
print(f"Cache size: {cache.size()} entries\n")

# Read first 10 addresses from DEM file
try:
    df = pd.read_csv('uploads/DEM EV 02252022_202202260722013902.csv', nrows=10)
    print("Found DEM file in uploads/\n")
except:
    print("DEM file not in uploads/, checking data/\n")
    # Try to find any recent CSV
    import glob
    csvs = glob.glob('uploads/*.csv')
    if csvs:
        df = pd.read_csv(csvs[0], nrows=10)
        print(f"Using: {csvs[0]}\n")
    else:
        print("No CSV files found!")
        sys.exit(1)

# Create job to clean addresses
job = ProcessingJob(
    csv_path='dummy.csv',
    county='Hidalgo',
    year='2022',
    election_type='primary',
    primary_party='democratic'
)

print("="*80)
print("ADDRESS COMPARISON")
print("="*80)

for idx, row in df.head(10).iterrows():
    original = row['ADDRESS']
    
    # Clean it the way processor does
    test_df = pd.DataFrame({'ADDRESS': [original]})
    cleaned_df = job.clean_addresses(test_df)
    if len(cleaned_df) > 0:
        cleaned = cleaned_df['cleaned_address'].iloc[0]
    else:
        cleaned = None
    
    if cleaned:
        # Normalize it
        normalized = cache.normalize_address(cleaned)
        
        # Check cache
        cached = cache.get(cleaned)
        
        print(f"\n{idx+1}. Original: {original}")
        print(f"   Cleaned:    {cleaned}")
        print(f"   Normalized: {normalized}")
        print(f"   In cache:   {'YES ✓' if cached else 'NO ✗'}")
        
        if not cached:
            # Try to find similar addresses in cache
            with open(Config.GEOCODING_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            # Extract street name for fuzzy matching
            street = original.split(',')[0] if ',' in original else original.split()[1:3]
            street_str = ' '.join(street) if isinstance(street, list) else street
            
            matches = [k for k in cache_data.keys() if street_str.upper() in k]
            if matches:
                print(f"   Similar in cache:")
                for match in matches[:2]:
                    print(f"     - {match}")
