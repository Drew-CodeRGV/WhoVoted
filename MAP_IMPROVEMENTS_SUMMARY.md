# Map Improvements Summary

## Changes Made

### 1. Cleaner Base Map
Changed from default OpenStreetMap tiles to CartoDB Positron tiles for a cleaner, less cluttered appearance.

**Before:**
```javascript
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);
```

**After:**
```javascript
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors, © CARTO',
    subdomains: 'abcd'
}).addTo(map);
```

### 2. Official Precinct Boundaries

The sample precinct boundaries need to be replaced with official data from the Texas Capitol Data Portal.

**Instructions:** See `PRECINCT_DATA_INSTRUCTIONS.md` for detailed steps.

**Quick Start:**
```bash
# Install required Python packages
pip install geopandas requests

# Run the conversion script
cd WhoVoted/scripts
python convert_precincts_to_geojson.py --county hidalgo --output ../public/data/precinct_boundaries.json
```

This will:
1. Download the official VTD shapefile from Texas Capitol Data Portal
2. Filter for Hidalgo County (FIPS code 215)
3. Convert to GeoJSON format
4. Save to the correct location

### 3. Alternative Base Map Options

If you want even more customization, here are other tile layer options:

#### CartoDB Dark Matter (for dark mode)
```javascript
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors, © CARTO',
    subdomains: 'abcd'
}).addTo(map);
```

#### CartoDB Voyager (balanced colors)
```javascript
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors, © CARTO',
    subdomains: 'abcd'
}).addTo(map);
```

#### Stamen Toner Lite (minimal, black and white)
```javascript
L.tileLayer('https://stamen-tiles-{s}.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: 'Map tiles by Stamen Design, © OpenStreetMap contributors',
    subdomains: 'abcd'
}).addTo(map);
```

#### OpenStreetMap with custom styling (remove labels)
You can also use Mapbox or other services to create custom styled maps with specific features hidden.

## Files Modified

1. `WhoVoted/public/map.js` - Changed tile layer to CartoDB Positron
2. `WhoVoted/public/styles.css` - Fixed overlapping UI elements
3. `WhoVoted/public/data/precinct_boundaries.json` - Sample data (needs replacement)
4. `WhoVoted/public/data/voting_locations.json` - Sample data (needs real polling places)

## Next Steps

1. **Get Official Precinct Boundaries:**
   - Run the conversion script (see above)
   - Or manually download and convert using QGIS (see PRECINCT_DATA_INSTRUCTIONS.md)

2. **Get Real Polling Place Data:**
   - Contact Hidalgo County Elections: (956) 318-2570
   - Or scrape from: https://www.hidalgocounty.us/3339/Unofficial-Early-Voting-Totals-Rosters
   - Update `WhoVoted/public/data/voting_locations.json`

3. **Add Turnout Data to Precincts:**
   - Match voter turnout data to precinct IDs
   - Update the `total_voters`, `voted_count`, and `turnout_percentage` fields

4. **Test the Map:**
   - Verify precinct boundaries display correctly
   - Check that polling places show at correct locations
   - Ensure voter markers display properly

## Resources

- Texas Capitol Data Portal: https://data.capitol.texas.gov/dataset/vtds
- Hidalgo County Elections: https://www.hidalgocounty.us/242/Elections
- CartoDB Basemaps: https://carto.com/help/building-maps/basemap-list/
- Leaflet Documentation: https://leafletjs.com/reference.html
