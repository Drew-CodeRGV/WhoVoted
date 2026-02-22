# Geocoding Quick Start Guide

## Problem: Addresses Clustering at Same Location?

This happens when geocoding falls back to ZIP-code level instead of street-level accuracy.

## Quick Fix (3 Steps)

### 1. Clear the Cache
```bash
cd WhoVoted
python scripts/clear_geocoding_cache.py
```

### 2. Choose Your Geocoding Provider

#### Option A: AWS Location Service (Best - Recommended)
- **Accuracy**: Excellent (95%+ street-level)
- **Cost**: 100,000 free requests/month
- **Setup Time**: 10 minutes

**Quick Setup:**
```bash
# Install boto3
pip install boto3

# Configure AWS
aws configure
# Enter your AWS credentials

# Add to .env
echo "AWS_LOCATION_PLACE_INDEX=WhoVotedPlaceIndex" >> backend/.env
```

**Detailed Guide:** [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md)

#### Option B: Free Services (Already Configured)
- **Accuracy**: Good (90%+ street-level)
- **Cost**: 100% Free
- **Setup Time**: 0 minutes (already working!)

Uses: Census Bureau → Photon → Nominatim

### 3. Re-upload Your Data
1. Go to http://localhost:5000/admin
2. Delete existing dataset (optional)
3. Upload CSV file
4. Check the map - addresses should be spread out!

## Check Quality

```bash
python scripts/check_geocoding_quality.py
```

## Which Option Should I Choose?

### Choose AWS Location Service if:
- ✓ You need the best possible accuracy
- ✓ You're uploading large datasets (>10K addresses)
- ✓ You want enterprise-grade reliability
- ✓ You have an AWS account (or willing to create one)

### Choose Free Services if:
- ✓ You're on a tight budget
- ✓ You have small datasets (<10K addresses)
- ✓ 90% accuracy is good enough
- ✓ You want zero setup

## Cost Comparison

| Provider | Free Tier | After Free Tier | Accuracy |
|----------|-----------|-----------------|----------|
| AWS Location | 100K/month | $0.50/1K | 95%+ |
| Census + Photon | Unlimited | Free | 90%+ |

**Example:** 30,000 addresses
- AWS: Free (within 100K limit)
- Free Services: Free

## Troubleshooting

### Still seeing clustering?
1. Did you clear the cache? `python scripts/clear_geocoding_cache.py`
2. Did you restart the server?
3. Did you re-upload the data?

### AWS not working?
1. Check boto3 installed: `pip list | grep boto3`
2. Check credentials: `aws sts get-caller-identity`
3. Check Place Index exists in AWS Console
4. Check logs for "AWS Location Service initialized" message

### Need more help?
- AWS Setup: [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md)
- Detailed Guide: [GEOCODING_ACCURACY_FIX.md](GEOCODING_ACCURACY_FIX.md)
- Quality Check: `python scripts/check_geocoding_quality.py`

## Summary

**Fastest Fix:** Clear cache + re-upload (uses free services, 90% accuracy)

**Best Fix:** AWS Location Service setup + clear cache + re-upload (95%+ accuracy)

Both options will eliminate address clustering!
