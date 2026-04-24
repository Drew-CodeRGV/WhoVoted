#!/usr/bin/env python3
"""
Download commissioner precinct boundaries from RGV911 ArcGIS service.
"""

import requests
import json

# The ArcGIS Experience ID from the URL
EXPERIENCE_ID = "b38d12fb41f541c08cccaf93e62e33fc"

# Try common ArcGIS REST service patterns
POSSIBLE_URLS = [
    # ArcGIS Online hosted feature services
    f"https://services.arcgis.com/rgv911/arcgis/rest/services/Commissioner_Precincts/FeatureServer/0",
    f"https://services1.arcgis.com/rgv911/arcgis/rest/services/Commissioner_Precincts/FeatureServer/0",
    f"https://rgv911.maps.arcgis.com/sharing/rest/content/items/{EXPERIENCE_ID}/data",
    
    # Try to get the item info
    f"https://rgv911.maps.arcgis.com/sharing/rest/content/items/{EXPERIENCE_ID}",
]

print("="*80)
print("DOWNLOADING COMMISSIONER PRECINCT BOUNDARIES")
print("="*80)

# First, try to get the item metadata
item_url = f"https://rgv911.maps.arcgis.com/sharing/rest/content/items/{EXPERIENCE_ID}?f=json"
print(f"\nFetching item metadata from: {item_url}")

try:
    response = requests.get(item_url, timeout=30)
    if response.status_code == 200:
        item_data = response.json()
        print(f"\nItem Title: {item_data.get('title', 'N/A')}")
        print(f"Item Type: {item_data.get('type', 'N/A')}")
        
        # Save the metadata
        with open('commissioner_item_metadata.json', 'w') as f:
            json.dump(item_data, f, indent=2)
        print("\nSaved metadata to commissioner_item_metadata.json")
        
        # Try to get the data
        data_url = f"https://rgv911.maps.arcgis.com/sharing/rest/content/items/{EXPERIENCE_ID}/data?f=json"
        print(f"\nFetching data from: {data_url}")
        
        data_response = requests.get(data_url, timeout=30)
        if data_response.status_code == 200:
            data = data_response.json()
            
            # Look for feature service URLs in the data
            data_str = json.dumps(data)
            if 'FeatureServer' in data_str or 'MapServer' in data_str:
                print("\nFound service URLs in data:")
                # Extract URLs
                import re
                urls = re.findall(r'https://[^"]+(?:FeatureServer|MapServer)[^"]*', data_str)
                for url in set(urls):
                    print(f"  {url}")
                    
                    # Try to query each service
                    if 'FeatureServer' in url or 'MapServer' in url:
                        # Add query parameters
                        query_url = f"{url}/query?where=1%3D1&outFields=*&f=geojson"
                        print(f"\n  Trying to query: {query_url}")
                        
                        try:
                            query_response = requests.get(query_url, timeout=30)
                            if query_response.status_code == 200:
                                geojson = query_response.json()
                                if 'features' in geojson and len(geojson['features']) > 0:
                                    print(f"  ✓ SUCCESS! Found {len(geojson['features'])} features")
                                    
                                    # Save the GeoJSON
                                    with open('commissioner_precincts.geojson', 'w') as f:
                                        json.dump(geojson, f, indent=2)
                                    print(f"\n  Saved to commissioner_precincts.geojson")
                                    exit(0)
                        except Exception as e:
                            print(f"  Error querying: {e}")
            
            # Save the data for inspection
            with open('commissioner_experience_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("\nSaved experience data to commissioner_experience_data.json")
            print("Inspect this file to find the FeatureServer URL")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("MANUAL STEPS REQUIRED")
print("="*80)
print("\n1. Open https://experience.arcgis.com/experience/b38d12fb41f541c08cccaf93e62e33fc")
print("2. Press F12 to open Developer Tools")
print("3. Go to Network tab")
print("4. Filter by 'Fetch/XHR'")
print("5. Refresh the page")
print("6. Look for requests to FeatureServer or MapServer")
print("7. Find the one with commissioner precinct data")
print("8. Copy the URL and add: /query?where=1%3D1&outFields=*&f=geojson")
print("9. Open that URL in browser to download GeoJSON")
