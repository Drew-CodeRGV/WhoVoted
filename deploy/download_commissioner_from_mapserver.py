#!/usr/bin/env python3
"""
Download commissioner precinct boundaries from RGV911 MapServer.
"""

import requests
import json

MAPSERVER_URL = "https://gis.rgv911.org/server/rest/services/Hidalgo_County_Emergency_Service_District_Map_MIL1/MapServer"

print("="*80)
print("DOWNLOADING COMMISSIONER PRECINCT BOUNDARIES")
print("="*80)

# Get the MapServer metadata
print(f"\nFetching MapServer metadata from: {MAPSERVER_URL}?f=json")

try:
    response = requests.get(f"{MAPSERVER_URL}?f=json", timeout=30)
    if response.status_code == 200:
        mapserver_data = response.json()
        
        # List all layers
        if 'layers' in mapserver_data:
            print(f"\nFound {len(mapserver_data['layers'])} layers:")
            
            for layer in mapserver_data['layers']:
                layer_id = layer.get('id')
                layer_name = layer.get('name')
                print(f"  Layer {layer_id}: {layer_name}")
                
                # Check if this is commissioner precincts
                if 'commissioner' in layer_name.lower() or 'precinct' in layer_name.lower():
                    print(f"\n  ✓ Found commissioner precinct layer!")
                    
                    # Query this layer
                    layer_url = f"{MAPSERVER_URL}/{layer_id}"
                    query_url = f"{layer_url}/query?where=1%3D1&outFields=*&f=geojson"
                    
                    print(f"  Querying: {query_url}")
                    
                    try:
                        query_response = requests.get(query_url, timeout=30)
                        if query_response.status_code == 200:
                            geojson = query_response.json()
                            if 'features' in geojson and len(geojson['features']) > 0:
                                print(f"  ✓ SUCCESS! Found {len(geojson['features'])} features")
                                
                                # Save the GeoJSON
                                filename = f'commissioner_precincts_layer{layer_id}.geojson'
                                with open(filename, 'w') as f:
                                    json.dump(geojson, f, indent=2)
                                print(f"  Saved to {filename}")
                                
                                # Show feature properties
                                if geojson['features']:
                                    props = geojson['features'][0]['properties']
                                    print(f"\n  Sample properties: {list(props.keys())}")
                                    print(f"  First feature: {props}")
                                
                                print("\n  ✓ DOWNLOAD COMPLETE!")
                    except Exception as e:
                        print(f"  Error querying layer: {e}")
        
except Exception as e:
    print(f"Error: {e}")
