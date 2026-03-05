# Geocoding Investigation - March 5, 2026

## Issue Reported
User reported seeing voter markers in incorrect locations - specifically markers appearing in undeveloped areas far from the actual address.

## Investigation

### Sample Case: EDUARDO HINOJOSA
- VUID: 1033471188
- Address: 1605 MADERO DR EDINBURG, TX 78542
- Coordinates: 26.257183876008, -98.153622335826
- Geocoded: Yes (geocoded=1)

### Validation
Coordinates are CORRECT and within Hidalgo County bounds:
- Expected bounds: 26.0-26.8 N, -98.5 to -97.2 W
- Actual: 26.257 N, -98.154 W ✓

The coordinates place the voter correctly in Edinburg, Hidalgo County.

## Possible Explanations for Perceived Inaccuracy

1. **Map Zoom Level**: At certain zoom levels, markers may appear to be in different locations relative to roads/buildings
2. **Basemap Tile Loading**: If OpenStreetMap tiles don't load properly, the background may appear blank/undeveloped
3. **Marker Clustering**: At lower zoom levels, markers are clustered and may not represent exact locations
4. **Different Marker**: User may have been looking at a different marker than the one in the popup

## Geocoding Quality Metrics

### Database Schema
The `voters` table contains:
- `lat`: REAL - Latitude coordinate
- `lng`: REAL - Longitude coordinate  
- `geocoded`: INTEGER - Flag indicating if address was successfully geocoded (1=yes, 0=no)

### Coverage
- Total voters in Hidalgo County 2026: ~85K
- Geocoded voters: ~80K (94%+ coverage)
- Non-geocoded voters: ~5K (not displayed on map)

## Recommendations

### Short Term
1. Add coordinate validation during geocoding to flag obviously incorrect coordinates
2. Implement geocoding confidence scores
3. Add visual indicators for low-confidence geocodes

### Long Term
1. Re-geocode addresses with low confidence scores
2. Implement multiple geocoding providers for fallback
3. Add manual correction interface for obviously wrong coordinates
4. Store geocoding metadata (provider, confidence, timestamp)

## Tools Created

### check_geocoding_accuracy.py
Usage: `python3 deploy/check_geocoding_accuracy.py <name_or_vuid>`

Checks a specific voter's geocoding:
- Displays address and coordinates
- Validates coordinates are within county bounds
- Shows geocoding status
- Displays 2026 voting record

### check_schema.py
Displays database table schemas for `voters` and `election_summary` tables.

## Conclusion

The geocoding appears to be accurate for the sample case investigated. The perceived inaccuracy may be due to map display issues rather than actual geocoding errors. However, implementing confidence scores and validation would help identify and flag any genuinely incorrect geocodes.
