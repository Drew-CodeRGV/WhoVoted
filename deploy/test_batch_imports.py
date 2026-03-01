#!/usr/bin/env python3
"""Test that batch_geocode_aws.py can import correctly."""
import sys, os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted')

try:
    from dotenv import load_dotenv
    load_dotenv('/opt/whovoted/.env')
    print("dotenv OK")
except Exception as e:
    print(f"dotenv FAIL: {e}")

try:
    import boto3
    print("boto3 OK")
except Exception as e:
    print(f"boto3 FAIL: {e}")

try:
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError
    print("botocore OK")
except Exception as e:
    print(f"botocore FAIL: {e}")

try:
    import sqlite3
    conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
    r = conn.execute("SELECT COUNT(*) FROM voters").fetchone()
    print(f"sqlite3 OK - {r[0]} voters")
    conn.close()
except Exception as e:
    print(f"sqlite3 FAIL: {e}")

# Test AWS credentials
try:
    client = boto3.client('location', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    place_index = os.environ.get('AWS_LOCATION_PLACE_INDEX', 'WhoVotedPlaceIndex')
    resp = client.search_place_index_for_text(
        IndexName=place_index, Text='100 Main St, McAllen, TX',
        MaxResults=1, FilterCountries=['USA'])
    if resp.get('Results'):
        coords = resp['Results'][0]['Place']['Geometry']['Point']
        print(f"AWS geocode OK - coords: {coords}")
    else:
        print("AWS geocode OK but no results")
except Exception as e:
    print(f"AWS geocode FAIL: {e}")
