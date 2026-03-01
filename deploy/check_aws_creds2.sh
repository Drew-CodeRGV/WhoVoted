#!/bin/bash
# Check if the .env credentials work when used explicitly (bypassing instance role)
cd /opt/whovoted
source venv/bin/activate

# Read the secret key and check if it's doubled
source /opt/whovoted/.env
HALF_LEN=$((${#AWS_SECRET_ACCESS_KEY} / 2))
FIRST_HALF="${AWS_SECRET_ACCESS_KEY:0:$HALF_LEN}"
SECOND_HALF="${AWS_SECRET_ACCESS_KEY:$HALF_LEN}"

echo "Secret key length: ${#AWS_SECRET_ACCESS_KEY}"
echo "First half == Second half: $([ "$FIRST_HALF" = "$SECOND_HALF" ] && echo 'YES (duplicated!)' || echo 'No')"

# Try with just the first half (the real key)
python3 -c "
import boto3

# Use explicit credentials, bypassing instance role
client = boto3.client(
    'location',
    region_name='us-east-1',
    aws_access_key_id='$AWS_ACCESS_KEY_ID',
    aws_secret_access_key='$FIRST_HALF'
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
        print(f'SUCCESS with half key: {r[\"Place\"][\"Label\"]} -> ({coords[1]}, {coords[0]})')
    else:
        print('No results returned')
except Exception as e:
    print(f'ERROR with half key: {e}')
"

# Also try with the full (doubled) key
python3 -c "
import boto3

client = boto3.client(
    'location',
    region_name='us-east-1',
    aws_access_key_id='$AWS_ACCESS_KEY_ID',
    aws_secret_access_key='$AWS_SECRET_ACCESS_KEY'
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
        print(f'SUCCESS with full key: {r[\"Place\"][\"Label\"]} -> ({coords[1]}, {coords[0]})')
    else:
        print('No results returned')
except Exception as e:
    print(f'ERROR with full key: {e}')
"
