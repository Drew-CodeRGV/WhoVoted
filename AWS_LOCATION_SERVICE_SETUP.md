# AWS Location Service Setup Guide

## Overview

AWS Location Service provides high-quality geocoding using data from Esri and HERE Technologies. It offers excellent accuracy for US addresses and has a generous free tier.

## Benefits

- **Excellent Accuracy**: Uses Esri and HERE data (industry-leading providers)
- **Generous Free Tier**: 100,000 requests/month free (enough for ~3 full county uploads)
- **No Rate Limits**: Unlike free services, no artificial rate limiting
- **Reliable**: Enterprise-grade infrastructure with 99.9% uptime SLA
- **Cost-Effective**: After free tier, only $0.50 per 1,000 requests

## Prerequisites

- AWS Account (free to create)
- AWS CLI installed (optional but recommended)
- Python boto3 library

## Step 1: Install boto3

```bash
cd WhoVoted/backend
pip install boto3
```

Or add to requirements.txt:
```
boto3>=1.26.0
```

## Step 2: Create AWS Location Service Place Index

### Option A: Using AWS Console (Easiest)

1. Go to [AWS Location Service Console](https://console.aws.amazon.com/location/home)
2. Click "Place indexes" in the left sidebar
3. Click "Create place index"
4. Configure:
   - **Name**: `WhoVotedPlaceIndex` (or your preferred name)
   - **Data provider**: Choose one:
     - **Esri** (Recommended for US addresses - most accurate)
     - **HERE** (Good alternative, slightly different coverage)
   - **Data storage location**: Choose your preferred region (e.g., `us-east-1`)
   - **Pricing plan**: "RequestBasedUsage" (pay-as-you-go with free tier)
5. Click "Create place index"
6. Copy the Place Index name (you'll need this for configuration)

### Option B: Using AWS CLI

```bash
# Create Place Index with Esri data provider
aws location create-place-index \
    --index-name WhoVotedPlaceIndex \
    --data-source Esri \
    --pricing-plan RequestBasedUsage \
    --region us-east-1

# Or with HERE data provider
aws location create-place-index \
    --index-name WhoVotedPlaceIndex \
    --data-source HERE \
    --pricing-plan RequestBasedUsage \
    --region us-east-1
```

## Step 3: Configure AWS Credentials

AWS Location Service requires AWS credentials to authenticate. Choose one method:

### Option A: AWS CLI Configuration (Recommended)

```bash
# Install AWS CLI if not already installed
# Windows: https://aws.amazon.com/cli/
# Mac: brew install awscli
# Linux: sudo apt-get install awscli

# Configure credentials
aws configure
```

Enter:
- **AWS Access Key ID**: Your access key
- **AWS Secret Access Key**: Your secret key
- **Default region**: `us-east-1` (or your preferred region)
- **Default output format**: `json`

### Option B: Environment Variables

Add to your `.env` file or system environment:

```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1
```

### Option C: IAM Role (For EC2/ECS deployments)

If running on AWS infrastructure, attach an IAM role with the following policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "geo:SearchPlaceIndexForText"
      ],
      "Resource": "arn:aws:geo:us-east-1:YOUR_ACCOUNT_ID:place-index/WhoVotedPlaceIndex"
    }
  ]
}
```

## Step 4: Configure WhoVoted

Add to `WhoVoted/backend/.env`:

```bash
# AWS Location Service Configuration
AWS_LOCATION_PLACE_INDEX=WhoVotedPlaceIndex
AWS_DEFAULT_REGION=us-east-1
```

Or update `WhoVoted/backend/config.py`:

```python
class Config:
    # ... existing config ...
    
    # AWS Location Service
    AWS_LOCATION_PLACE_INDEX = os.getenv('AWS_LOCATION_PLACE_INDEX', 'WhoVotedPlaceIndex')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
```

## Step 5: Test the Configuration

Create a test script `test_aws_geocoding.py`:

```python
#!/usr/bin/env python3
"""Test AWS Location Service geocoding."""

import sys
sys.path.insert(0, 'backend')

from geocoder import GeocodingCache, NominatimGeocoder
from config import Config

# Initialize geocoder
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
geocoder = NominatimGeocoder(
    cache=cache,
    aws_place_index=Config.AWS_LOCATION_PLACE_INDEX if hasattr(Config, 'AWS_LOCATION_PLACE_INDEX') else None
)

# Test address
test_address = "123 Main Street, McAllen, TX 78501"
print(f"Testing geocoding for: {test_address}")

result = geocoder.geocode(test_address)

if result:
    print(f"\n✓ Success!")
    print(f"  Source: {result.get('source')}")
    print(f"  Latitude: {result['lat']}")
    print(f"  Longitude: {result['lng']}")
    print(f"  Display Name: {result['display_name']}")
    if result.get('source') == 'aws_location':
        print(f"  Relevance: {result.get('relevance', 'N/A')}")
else:
    print("\n✗ Geocoding failed")

# Show stats
stats = geocoder.get_stats()
print(f"\nStatistics:")
print(f"  AWS Location calls: {stats.get('aws_api_calls', 0)}")
print(f"  AWS Location success: {stats.get('aws_success', 0)}")
```

Run the test:
```bash
cd WhoVoted
python test_aws_geocoding.py
```

Expected output:
```
Testing geocoding for: 123 Main Street, McAllen, TX 78501

✓ Success!
  Source: aws_location
  Latitude: 26.2034
  Longitude: -98.2300
  Display Name: 123 Main St, McAllen, TX 78501, USA
  Relevance: 0.95

Statistics:
  AWS Location calls: 1
  AWS Location success: 1
```

## Step 6: Clear Cache and Re-upload Data

To use AWS Location Service for existing data:

```bash
# Clear the geocoding cache
cd WhoVoted
python scripts/clear_geocoding_cache.py

# Restart the Flask server
# Then re-upload your CSV files through the admin panel
```

## Geocoding Provider Order

With AWS Location Service configured, the fallback order is:

1. **Cache** - Check if already geocoded
2. **AWS Location Service** - Best accuracy (Esri/HERE data)
3. **US Census Bureau** - Good for US addresses
4. **Photon** - OpenStreetMap-based
5. **Nominatim** - OpenStreetMap-based, rate-limited
6. **ZIP code fallback** - Last resort

## Cost Estimation

### Free Tier
- **100,000 requests/month** free forever
- Typical county upload: ~30,000 addresses
- **You can upload ~3 full counties per month for free**

### After Free Tier
- **$0.50 per 1,000 requests**
- 30,000 addresses = $15
- Cache reduces costs for subsequent uploads

### Cost Optimization Tips
1. **Use the cache** - Addresses are cached permanently
2. **Don't clear cache unnecessarily** - Only clear when improving geocoding
3. **Batch uploads** - Upload multiple files at once to maximize cache hits
4. **Monitor usage** - Check AWS billing dashboard regularly

## Monitoring Usage

### AWS Console
1. Go to [AWS Location Service Console](https://console.aws.amazon.com/location/home)
2. Click "Place indexes"
3. Select your index
4. View "Metrics" tab for usage statistics

### AWS CLI
```bash
# Get usage metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Location \
    --metric-name RequestCount \
    --dimensions Name=PlaceIndex,Value=WhoVotedPlaceIndex \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-12-31T23:59:59Z \
    --period 86400 \
    --statistics Sum
```

## Troubleshooting

### Error: "boto3 not installed"
```bash
pip install boto3
```

### Error: "AWS credentials not found"
Run `aws configure` and enter your credentials.

### Error: "Place Index not found"
- Verify the Place Index name in AWS Console
- Check that AWS_LOCATION_PLACE_INDEX in .env matches the index name
- Ensure you're using the correct AWS region

### Error: "Access Denied"
Your AWS credentials don't have permission. Add the IAM policy from Step 3.

### Geocoding still using Census/Photon
- Verify AWS_LOCATION_PLACE_INDEX is set in .env
- Restart the Flask server
- Check logs for "AWS Location Service initialized" message
- If you see "AWS Location Service Place Index not configured", check your .env file

## Comparison: AWS vs Free Services

| Feature | AWS Location | Census Bureau | Photon | Nominatim |
|---------|-------------|---------------|--------|-----------|
| **Accuracy** | Excellent (Esri/HERE) | Good | Good | Variable |
| **Rate Limit** | None | None | None | 1/second |
| **Free Tier** | 100K/month | Unlimited | Unlimited | Unlimited |
| **Cost After** | $0.50/1K | Free | Free | Free |
| **Reliability** | 99.9% SLA | Good | Good | Variable |
| **US Coverage** | Excellent | Excellent | Good | Good |
| **Support** | AWS Support | None | Community | Community |

## Recommendation

**Use AWS Location Service if:**
- You need the best possible accuracy
- You're uploading large datasets (>10K addresses)
- You want reliable, enterprise-grade service
- You're okay with AWS costs after free tier

**Use Free Services if:**
- You're on a tight budget
- You have small datasets (<10K addresses)
- You don't mind occasional inaccuracies
- You're okay with rate limits

## Need Help?

- [AWS Location Service Documentation](https://docs.aws.amazon.com/location/)
- [AWS Location Service Pricing](https://aws.amazon.com/location/pricing/)
- [AWS Support](https://aws.amazon.com/support/)
