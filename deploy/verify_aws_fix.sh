#!/bin/bash
# Verify the AWS Location Service fix is working
cd /opt/whovoted
source venv/bin/activate
source .env

python3 -c "
import os
import boto3
from botocore.config import Config as BotoConfig

# This is what the geocoder now does — explicit credentials
client = boto3.client(
    'location',
    region_name='us-east-1',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    config=BotoConfig(max_pool_connections=50)
)

addresses = [
    '100 Main Street, McAllen, Texas 78501',
    '2000 South 10th Street, McAllen, Texas 78503',
    '500 North Closner Boulevard, Edinburg, Texas 78541'
]

for addr in addresses:
    try:
        resp = client.search_place_index_for_text(
            IndexName='WhoVotedPlaceIndex',
            Text=addr,
            MaxResults=1,
            FilterCountries=['USA']
        )
        if resp.get('Results'):
            r = resp['Results'][0]
            coords = r['Place']['Geometry']['Point']
            print(f'OK: {addr} -> ({coords[1]:.6f}, {coords[0]:.6f})')
        else:
            print(f'NO RESULTS: {addr}')
    except Exception as e:
        print(f'ERROR: {addr} -> {e}')
"
