#!/bin/bash
# Verify the AWS Location Service fix is working
cd /opt/whovoted
source venv/bin/activate

# Export the env vars so Python subprocess can see them
set -a
source .env
set +a

echo "Checking env vars visible to Python..."
python3 -c "
import os
key = os.environ.get('AWS_ACCESS_KEY_ID', '')
secret = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
print(f'AWS_ACCESS_KEY_ID present: {bool(key)} (len={len(key)})')
print(f'AWS_SECRET_ACCESS_KEY present: {bool(secret)} (len={len(secret)})')

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
    else:
        print('No results returned')
except Exception as e:
    print(f'ERROR: {e}')
"
