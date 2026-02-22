# How to Get Official Precinct Boundary Data

## Manual Download Instructions (Recommended)

Due to SSL certificate issues with automated downloads, it's easier to download manually:

1. **Visit the Texas Capitol Data Portal:**
   - Go to: https://data.capitol.texas.gov/dataset/vtds
   
2. **Download the VTDs_24PG.zip file:**
   - Look for the link "VTDs_24PG.zip - 2024 Primary & General Elections VTDs"
   - Click to download (file is approximately 50-100 MB)
   - Save to your Downloads folder

3. **Run the conversion script with the local file:**
   ```bash
   cd WhoVoted/scripts
   python convert_precincts_to_geojson.py --county hidalgo --shapefile "C:/Users/YourUsername/Downloads/VTDs_24PG.shp" --output ../public/data/precinct_boundaries.json
   ```
   
   Replace `YourUsername` with your actual Windows username, or use the full path to where you extracted the shapefile.

4. **Extract the ZIP file first:**
   - Right-click VTDs_24PG.zip → Extract All
   - Note the location of the extracted files
   - Look for the file ending in `.shp` (e.g., `VTDs_24PG.shp`)

## Quick Alternative: Use Existing County Boundaries

If you just need something to display quickly, you can use the existing county outlines file that's already in the project:

```javascript
// In map.js, update loadPrecinctBoundaries to use county outlines
async function loadPrecinctBoundaries(dataUrl = '../data/tx-county-outlines.json') {
    // ... rest of the function
}
```

This will show county boundaries instead of precinct boundaries as a temporary solution.

### Download Links

**2024 Primary & General Elections VTDs (Voting Tabulation Districts):**
- Shapefile: https://data.capitol.texas.gov/dataset/vtds
- Direct download: `VTDs_24PG.zip`

### What You Need

1. **VTDs_24PG.zip** - Contains the shapefile with all Texas precinct boundaries
2. **VTDs_24PG_Pop.zip** - Contains population data by precinct (optional)

### Converting Shapefile to GeoJSON

You'll need to convert the shapefile to GeoJSON format and filter for Hidalgo County only.

#### Option 1: Using QGIS (Recommended)

1. Download and install QGIS (free): https://qgis.org/
2. Download `VTDs_24PG.zip` from the Capitol Data Portal
3. Extract the ZIP file
4. Open QGIS and load the shapefile:
   - Layer → Add Layer → Add Vector Layer
   - Select the `.shp` file from the extracted folder
5. Filter for Hidalgo County:
   - Right-click the layer → Filter
   - Enter: `"CNTY" = 215` (215 is Hidalgo County's FIPS code)
   - Click OK
6. Export to GeoJSON:
   - Right-click the layer → Export → Save Features As
   - Format: GeoJSON
   - File name: `precinct_boundaries.json`
   - CRS: EPSG:4326 (WGS 84)
   - Click OK
7. Copy the file to: `WhoVoted/public/data/precinct_boundaries.json`

#### Option 2: Using ogr2ogr (Command Line)

If you have GDAL installed:

```bash
# Extract the ZIP file first
unzip VTDs_24PG.zip

# Convert to GeoJSON and filter for Hidalgo County (FIPS code 215)
ogr2ogr -f GeoJSON \
  -where "CNTY = 215" \
  -t_srs EPSG:4326 \
  precinct_boundaries.json \
  VTDs_24PG.shp
```

#### Option 3: Using Python with geopandas

```python
import geopandas as gpd

# Read the shapefile
gdf = gpd.read_file('VTDs_24PG.shp')

# Filter for Hidalgo County (FIPS code 215)
hidalgo = gdf[gdf['CNTY'] == 215]

# Convert to WGS84 (EPSG:4326)
hidalgo = hidalgo.to_crs('EPSG:4326')

# Save as GeoJSON
hidalgo.to_file('precinct_boundaries.json', driver='GeoJSON')
```

### County FIPS Codes

If you need other Texas counties:
- **Hidalgo County**: 215
- **Cameron County**: 061
- **Starr County**: 427
- **Willacy County**: 489

Full list: https://www.census.gov/library/reference/code-lists/ansi.html

### File Structure

The GeoJSON file should have this structure:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "CNTY": 215,
        "VTD": "0001",
        "VTDKEY": 2150001,
        "CNTYVTD": "2150001"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[...]]
      }
    }
  ]
}
```

### Adding Turnout Data

To add turnout statistics to each precinct:

1. Get voter turnout data from Hidalgo County Elections
2. Match precincts by VTD number
3. Add properties to each feature:
   ```json
   "properties": {
     "precinct_id": "0001",
     "precinct": "Precinct 1",
     "total_voters": 1250,
     "voted_count": 487,
     "turnout_percentage": 38.96
   }
   ```

### Alternative: Use Existing County Outlines

The project already has `tx-county-outlines.json` in the data folder. You can use this as a starting point and overlay precinct boundaries on top.

### Need Help?

- Texas Capitol Data Portal: https://data.capitol.texas.gov/
- QGIS Documentation: https://docs.qgis.org/
- Contact Hidalgo County Elections: (956) 318-2570
