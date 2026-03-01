#!/usr/bin/env python3
"""Quick test to verify batch_geocode_aws.py can import and start."""
import sys, os, traceback
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted')

print("Step 1: Loading dotenv...")
from dotenv import load_dotenv
load_dotenv('/opt/whovoted/.env')
print(f"  AWS_REGION={os.environ.get('AWS_REGION','?')}")
print(f"  AWS_ACCESS_KEY_ID={os.environ.get('AWS_ACCESS_KEY_ID','?')[:8]}...")
print(f"  PLACE_INDEX={os.environ.get('AWS_LOCATION_PLACE_INDEX','?')}")

print("Step 2: Importing boto3...")
try:
    import boto3
    print(f"  boto3 OK: {boto3.__version__}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print("Step 3: Testing AWS Location Service...")
try:
    from botocore.config import Config as BotoConfig
    client = boto3.client('location', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    resp = client.search_place_index_for_text(
        IndexName=os.environ.get('AWS_LOCATION_PLACE_INDEX', 'WhoVotedPlaceIndex'),
        Text='100 N 10TH ST, MCALLEN, TX 78501',
        MaxResults=1,
        FilterCountries=['USA']
    )
    if resp.get('Results'):
        place = resp['Results'][0]['Place']
        coords = place['Geometry']['Point']
        print(f"  Geocode OK: {coords[1]:.6f}, {coords[0]:.6f}")
    else:
        print("  No results returned")
except Exception as e:
    print(f"  FAILED: {e}")
    traceback.print_exc()

print("Step 4: Testing DB connection...")
try:
    import sqlite3
    conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=30)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT COUNT(*) as cnt FROM voters WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL)").fetchone()
    print(f"  Ungeocoded voters: {r['cnt']:,}")
    conn.close()
except Exception as e:
    print(f"  FAILED: {e}")

print("Step 5: Importing batch_geocode_aws module...")
try:
    sys.path.insert(0, '/opt/whovoted/deploy')
    import batch_geocode_aws
    print("  Import OK")
except Exception as e:
    print(f"  FAILED: {e}")
    traceback.print_exc()

print("\nAll checks passed!")
