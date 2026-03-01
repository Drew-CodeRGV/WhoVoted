#!/bin/bash
# Check what the app actually sees when started from the supervisor working directory
cd /opt/whovoted/backend
source /opt/whovoted/venv/bin/activate

python3 -c "
import os
from dotenv import load_dotenv

# This is what config.py does
load_dotenv()

key = os.environ.get('AWS_ACCESS_KEY_ID', '')
secret = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
print(f'After load_dotenv():')
print(f'  AWS_ACCESS_KEY_ID: {bool(key)} (len={len(key)})')
print(f'  AWS_SECRET_ACCESS_KEY: {bool(secret)} (len={len(secret)})')

if key and secret:
    import boto3
    from botocore.config import Config as BotoConfig
    client = boto3.client(
        'location',
        region_name='us-east-1',
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        config=BotoConfig(max_pool_connections=50)
    )
    try:
        resp = client.search_place_index_for_text(
            IndexName='WhoVotedPlaceIndex',
            Text='100 Main Street, McAllen, Texas 78501',
            MaxResults=1,
            FilterCountries=['USA']
        )
        if resp.get('Results'):
            r = resp['Results'][0]
            coords = r['Place']['Geometry']['Point']
            print(f'SUCCESS: {r[\"Place\"][\"Label\"]} -> ({coords[1]:.6f}, {coords[0]:.6f})')
    except Exception as e:
        print(f'ERROR: {e}')
else:
    print('No AWS credentials found after load_dotenv()')
"
