# Geocoding Accuracy Fix

## Problem
Multiple different addresses are being geocoded to the same location because:
1. Geocoding services can't find exact addresses and fall back to ZIP code level
2. The cache stores these imprecise results and reuses them
3. Address formatting was insufficient (missing city names, abbreviated street names)

## Solutions Available

### Option 1: AWS Location Service (Recommended - Best Accuracy)

AWS Location Service provides the highest accuracy using Esri and HERE Technologies data. It has a generous free tier (100,000 requests/month) and excellent reliability.

**Benefits:**
- Excellent accuracy (industry-leading Esri/HERE data)
- 100,000 free requests/month (enough for ~3 full county uploads)
- No rate limits
- Enterprise-grade reliability

**Setup:** See [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md) for detailed instructions.

**Quick Setup:**
1. Install boto3: `pip install boto3`
2. Create Place Index in AWS Console
3. Configure AWS credentials: `aws configure`
4. Add to `.env`: `AWS_LOCATION_PLACE_INDEX=WhoVotedPlaceIndex`
5. Clear cache and re-upload data

### Option 2: Free Services (Already Implemented)

The system includes multiple free geocoding services with improved address formatting:

**Improvements Made:**
1. **Added Photon Geocoder** - Free, unlimited, OpenStreetMap-based
2. **Improved Address Formatting** - Adds city names based on county
3. **Updated Geocoding Order** - Prioritizes best free services

**Geocoding Order (without AWS):**
- Cache → US Census Bureau → Photon → Nominatim → ZIP fallback

## How to Apply the Fix

### Step 1: Choose Your Geocoding Provider

**For Best Accuracy:** Follow [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md)

**For Free Services:** Continue with steps below (already implemented)

### Step 2: Clear Existing Geocoding Cache

The current cache contains many ZIP-code-level results. Clear it to force re-geocoding:

```bash
# From WhoVoted directory
python scripts/clear_geocoding_cache.py
```

Or manually:
```bash
rm data/geocoding_cache.json
```

### Step 3: Re-upload Your Data

After clearing the cache:
1. Go to the admin panel (http://localhost:5000/admin)
2. Delete the existing dataset (optional, but recommended)
3. Re-upload the CSV file
4. The system will now geocode with improved accuracy

### Step 4: Monitor Geocoding Quality

Check the processing logs to see which geocoding provider is being used:
- "AWS Location Service success" = Best accuracy (if configured)
- "Census geocoder success" = Good accuracy for US addresses
- "Photon geocoder success" = Good accuracy, street-level
- "Nominatim success" = Variable accuracy
- "ZIP code fallback" = Poor accuracy (should be rare now)

You can also run the quality check script:
```bash
cd WhoVoted
python scripts/check_geocoding_quality.py
```

## Expected Results

With these improvements, you should see:
- **With AWS Location Service**: 95%+ street-level accuracy
- **With Free Services**: 90%+ street-level accuracy
- Minimal ZIP-code fallbacks (< 5%)
- Addresses properly spread out on the map
- No clustering of different addresses at the same location

## Technical Details

### Geocoding Provider Order

**With AWS Location Service configured:**
1. Cache → AWS Location → Census → Photon → Nominatim → ZIP fallback

**Without AWS Location Service:**
1. Cache → Census → Photon → Nominatim → ZIP fallback

### Address Formatting Improvements
- Adds city name based on county (Hidalgo → McAllen, Cameron → Brownsville)
- Expands abbreviations (ST → STREET, AVE → AVENUE, RD → ROAD, etc.)
- Ensures proper format: "123 MAIN STREET, MCALLEN, TX 78501"
- Preserves ZIP codes and moves them to the end

### Cost Comparison

| Provider | Free Tier | Cost After | Accuracy | Rate Limit |
|----------|-----------|------------|----------|------------|
| **AWS Location** | 100K/month | $0.50/1K | Excellent | None |
| **Census Bureau** | Unlimited | Free | Good | None |
| **Photon** | Unlimited | Free | Good | None |
| **Nominatim** | Unlimited | Free | Variable | 1/second |

## Testing

After implementing the fix:
1. Clear the geocoding cache
2. Upload a small test file (100 addresses)
3. Check the map - addresses should be spread out
4. Click on markers - verify they're at the correct locations
5. Check processing logs for success messages
6. Run `python scripts/check_geocoding_quality.py` to see statistics

## Troubleshooting

### Addresses Still Clustering

1. **Check that you cleared the cache**
   ```bash
   python scripts/clear_geocoding_cache.py
   ```

2. **Restart the Flask server**
   ```bash
   # Stop the server (Ctrl+C)
   # Start it again
   python backend/app.py
   ```

3. **Verify address format in CSV**
   - Include street names and ZIP codes
   - Avoid PO Boxes (they geocode to post office location)

4. **Check the logs for errors**
   - Look for "All geocoding providers failed" messages
   - Check which provider is being used most

5. **Run quality check**
   ```bash
   python scripts/check_geocoding_quality.py
   ```

### AWS Location Service Issues

See [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md) troubleshooting section.

Common issues:
- boto3 not installed: `pip install boto3`
- AWS credentials not found: Run `aws configure`
- Place Index not found: Check index name in AWS Console
- Access denied: Add IAM permissions

### Common Issues

**Issue**: "Photon API timeout"
**Solution**: Photon API is occasionally slow. The system will automatically fall back to Nominatim.

**Issue**: "All geocoding providers failed"
**Solution**: Check that the address has a valid street name and ZIP code. PO Boxes may fail.

**Issue**: Still seeing clustering after clearing cache
**Solution**: Make sure you restarted the server and re-uploaded the data. Old cached results will persist until cleared.

## Recommendations

### For Production Use
1. **Use AWS Location Service** for best accuracy and reliability
2. **Monitor usage** to stay within free tier
3. **Keep cache enabled** to reduce API calls
4. **Clear cache only when needed** (after geocoding improvements)

### For Development/Testing
1. **Use free services** (Census + Photon + Nominatim)
2. **Test with small datasets** first
3. **Check quality** with the quality check script
4. **Upgrade to AWS** if accuracy is insufficient

## Need Help?

If you're still experiencing issues:
1. Run `python scripts/check_geocoding_quality.py` to see detailed statistics
2. Check the Flask server logs for error messages
3. Verify that addresses in your CSV include street names and ZIP codes
4. Try uploading a small test file (10-20 addresses) to isolate the issue
5. See [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md) for AWS-specific help
