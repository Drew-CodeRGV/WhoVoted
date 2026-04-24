# How to Download Commissioner Precinct Boundaries from ArcGIS

Since the ArcGIS Experience page uses dynamic JavaScript, you need to manually extract the GeoJSON.

## Method 1: Browser Developer Tools (EASIEST)

1. Open https://experience.arcgis.com/experience/b38d12fb41f541c08cccaf93e62e33fc in Chrome/Edge
2. Press F12 to open Developer Tools
3. Go to the "Network" tab
4. Filter by "Fetch/XHR"
5. Refresh the page or interact with the map
6. Look for requests to URLs containing:
   - `FeatureServer` or `MapServer`
   - `query` with `f=json` or `f=geojson`
7. Click on the request and view the Response
8. Copy the GeoJSON data
9. Save it as `commissioner_precincts.geojson`

## Method 2: Find the REST Service URL

1. Open the page and right-click > "View Page Source"
2. Search for "FeatureServer" or "MapServer"
3. Find URLs like: `https://services.arcgis.com/.../FeatureServer/0`
4. Open that URL in a new tab
5. Add `/query?where=1%3D1&outFields=*&f=geojson` to the end
6. Download the resulting GeoJSON

## Method 3: Use ArcGIS REST API Directly

If you find the service URL (something like):
```
https://services.arcgis.com/[org]/arcgis/rest/services/[service]/FeatureServer/[layer]
```

You can query it directly:
```
https://services.arcgis.com/[org]/arcgis/rest/services/[service]/FeatureServer/[layer]/query?where=1%3D1&outFields=*&f=geojson
```

## Method 4: Contact Hidalgo County

Email their GIS department and request the commissioner precinct boundaries as:
- GeoJSON
- Shapefile
- KML

## Once You Have the File

Save it as `WhoVoted/commissioner_precincts_official.geojson` and I'll:
1. Extract CPct-2 boundary
2. Update districts.json
3. Recalculate vote counts
4. Regenerate the report
