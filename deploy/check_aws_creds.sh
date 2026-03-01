#!/bin/bash
# Check AWS credentials
source /opt/whovoted/.env
echo "AWS_ACCESS_KEY_ID length: ${#AWS_ACCESS_KEY_ID}"
echo "AWS_SECRET_ACCESS_KEY length: ${#AWS_SECRET_ACCESS_KEY}"
echo "AWS_REGION: $AWS_REGION"

# Test if boto3 can authenticate
cd /opt/whovoted
source venv/bin/activate
python3 -c "
import boto3
from botocore.config import Config as BotoConfig

client = boto3.client('location', region_name='us-east-1')
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
        print(f'SUCCESS: {r[\"Place\"][\"Label\"]} -> ({coords[1]}, {coords[0]})')
    else:
        print('No results returned')
except Exception as e:
    print(f'ERROR: {e}')
"
