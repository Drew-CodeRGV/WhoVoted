#!/usr/bin/env python3
"""
Download commissioner precinct boundaries from RGV911 web map.
"""

import requests
import json

WEBMAP_ID = "8aa37c0722b24639b4bbddfcaf412915"
PORTAL_URL = "https://RGV911.maps.arcgis.com"

print("="*80)
print("DOWNLOADING COMMISSIONER PRECINCT BOUNDARIES FROM WEB MAP")
print("="*80)

# Get the web map data
webmap_url = f"{PORTAL_URL}/sharing/rest/content/items/{WEBMAP_ID}/data?f=json"
print(f"\nFetching web map from: {webmap_url}")

try:
    response = requests.get(webmap_url, timeout=30)
    if response.status_code == 200:
        webmap_data = response.json()
        
        # Save for inspection
        with open('webmap_data.json', 'w') as f:
            json.dump(webmap_data, f, indent=2)
        print("Saved web map data to webmap_data.json")
        
        # Look for operational layers
        if 'operationalLayers' in webmap_data:
            print(f"\nFound {len(webmap_data['operationalLayers'])} operational layers:")
            
            for i, layer in enumerate(webmap_data['operationalLayers']):
                title = layer.get('title', 'Untitled')
                url = layer.get('url', 'No URL')
                layer_type = layer.get('layerType', 'Unknown')
                
                print(f"\n  Layer {i}: {title}")
                print(f"    Type: {layer_type}")
                print(f"    URL: {url}")
                
                # Check if this is commissioner precincts
                if 'commissioner' in title.lower() or 'precinct' in title.lower():
                    print(f"\n  ✓ Found commissioner precinct layer!")
                    
                    # Try to query it
                    if url and 'FeatureServer' in url:
                        query_url = f"{url}/query?where=1%3D1&outFields=*&f=geojson"
                        print(f"  Querying: {query_url}")
                        
                        try:
                            query_response = requests.get(query_url, timeout=30)
                            if query_response.status_code == 200:
                                geojson = query_response.json()
                                if 'features' in geojson:
                                    print(f"  ✓ SUCCESS! Found {len(geojson['features'])} features")
                                    
                                    # Save the GeoJSON
                                    with open('commissioner_precincts.geojson', 'w') as f:
                                        json.dump(geojson, f, indent=2)
                                    print(f"\n  Saved to commissioner_precincts.geojson")
                                    
                                    # Show feature properties
                                    if geojson['features']:
                                        props = geojson['features'][0]['properties']
                                        print(f"\n  Sample properties: {list(props.keys())}")
                                    
                                    exit(0)
                        except Exception as e:
                            print(f"  Error querying: {e}")
        
        print("\n" + "="*80)
        print("Check webmap_data.json for layer URLs")
        print("="*80)
        
except Exception as e:
    print(f"Error: {e}")
