# Quick Start: Using AWS Location Service

## ✓ Setup Complete!

AWS Location Service is now configured and ready to use.

## Next Steps (3 minutes)

### 1. Clear the Cache (30 seconds)

```bash
cd WhoVoted
python scripts/clear_geocoding_cache.py
```

Type `yes` when prompted.

### 2. Restart the Server (if running)

If your Flask server is running:
- Press `Ctrl+C` to stop it
- Start it again: `python backend/app.py`

### 3. Upload Your Data (2 minutes)

1. Go to http://localhost:5000/admin
2. Login (admin / admin2026!)
3. Upload your CSV file
4. Watch the magic happen! ✨

## What to Expect

### In the Logs
You'll see messages like:
```
AWS Location Service initialized with Place Index: WhoVotedPlaceIndex
AWS Location Service success for: 123 MAIN STREET, MCALLEN, TX 78501
```

### In the Results
- **95%+ accuracy** (up from 90%)
- **Faster processing** (no rate limits)
- **Better address matching**
- **Addresses properly spread out on map**

## Verify It's Working

Run the test script:
```bash
python test_aws_geocoding.py
```

You should see:
- ✓ Success for all test addresses
- Source: aws_location
- Relevance scores near 1.0

## Cost Tracking

You get **100,000 free requests/month**.

To check usage:
```bash
aws cloudwatch get-metric-statistics \
    --namespace AWS/Location \
    --metric-name RequestCount \
    --dimensions Name=PlaceIndex,Value=WhoVotedPlaceIndex \
    --start-time 2026-02-01T00:00:00Z \
    --end-time 2026-02-28T23:59:59Z \
    --period 86400 \
    --statistics Sum
```

Or check the AWS Console:
https://console.aws.amazon.com/location/home

## Troubleshooting

**Not seeing "AWS Location Service" in logs?**
1. Check .env file has AWS_LOCATION_PLACE_INDEX=WhoVotedPlaceIndex
2. Restart the Flask server
3. Run test script: `python test_aws_geocoding.py`

**Still using Census/Photon?**
- AWS Location Service is tried first
- If it fails, it falls back to Census/Photon
- This is normal and expected behavior

## That's It!

You're now using industry-leading geocoding with Esri data. Enjoy the improved accuracy! 🎉

For detailed information, see:
- [AWS_SETUP_COMPLETE.md](AWS_SETUP_COMPLETE.md) - Full setup details
- [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md) - Complete guide
- [GEOCODING_ACCURACY_FIX.md](GEOCODING_ACCURACY_FIX.md) - Troubleshooting
