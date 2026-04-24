#!/usr/bin/env python3
"""Pull Census ACS data for school-age children by tract in McAllen, build heatmap cache.

Uses 2020 Decennial Census P12 (Sex by Age) table.
Ages adjusted +6 years for 2026 estimates.

2020 ages -> 2026 estimated school level:
  Under 5 (2020) -> 6-10 (2026) = Elementary
  5-9 (2020) -> 11-15 (2026) = Middle School  
  10-14 (2020) -> 16-20 (2026) = High School / aged out
  15-17 (2020) -> 21-23 (2026) = Aged out
  
So for 2026 school-age:
  Elementary (5-10): was Under 5 in 2020 -> P12_003N + P12_027N (male+female under 5)
  Middle (11-14): was 5-9 in 2020 -> P12_004N + P12_028N  
  High (15-17): was 10-14 in 2020 -> P12_005N + P12_029N (partial - some aged out)
"""
import requests, json
from pathlib import Path

CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_students.json'

# Census API - 2020 Decennial, Hidalgo County TX (FIPS 48215)
# P12: Sex by Age
CENSUS_URL = 'https://api.census.gov/data/2020/dec/dhc'
VARIABLES = 'NAME,P12_003N,P12_004N,P12_005N,P12_006N,P12_027N,P12_028N,P12_029N,P12_030N'
# P12_003N = Male Under 5, P12_004N = Male 5-9, P12_005N = Male 10-14, P12_006N = Male 15-17
# P12_027N = Female Under 5, P12_028N = Female 5-9, P12_029N = Female 10-14, P12_030N = Female 15-17

def main():
    print("Fetching Census tract data for Hidalgo County...")
    
    params = {
        'get': VARIABLES,
        'for': 'tract:*',
        'in': 'state:48+county:215'
    }
    
    resp = requests.get(CENSUS_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    headers = data[0]
    rows = data[1:]
    print(f"Got {len(rows)} census tracts")
    
    # Get tract centroids from TIGERweb
    print("Fetching tract centroids...")
    tiger_url = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/8/query'
    tiger_params = {
        'where': "STATE='48' AND COUNTY='215'",
        'outFields': 'TRACT,CENTLAT,CENTLON',
        'returnGeometry': 'false',
        'f': 'json'
    }
    tiger_resp = requests.get(tiger_url, params=tiger_params, timeout=30)
    tiger_data = tiger_resp.json()
    
    centroids = {}
    for feat in tiger_data.get('features', []):
        a = feat['attributes']
        centroids[a['TRACT']] = (float(a['CENTLAT']), float(a['CENTLON']))
    print(f"Got {len(centroids)} tract centroids")
    
    # McAllen approximate bounding box
    MCALLEN_BOUNDS = {
        'lat_min': 26.10, 'lat_max': 26.32,
        'lng_min': -98.30, 'lng_max': -98.15
    }
    
    tracts = []
    total_elem = total_ms = total_hs = 0
    
    for row in rows:
        tract_fips = row[headers.index('tract')]
        
        if tract_fips not in centroids:
            continue
        lat, lng = centroids[tract_fips]
        
        # Filter to McAllen area
        if not (MCALLEN_BOUNDS['lat_min'] <= lat <= MCALLEN_BOUNDS['lat_max'] and
                MCALLEN_BOUNDS['lng_min'] <= lng <= MCALLEN_BOUNDS['lng_max']):
            continue
        
        # 2020 counts -> 2026 age-adjusted
        m_under5 = int(row[headers.index('P12_003N')])
        m_5_9 = int(row[headers.index('P12_004N')])
        m_10_14 = int(row[headers.index('P12_005N')])
        m_15_17 = int(row[headers.index('P12_006N')])
        f_under5 = int(row[headers.index('P12_027N')])
        f_5_9 = int(row[headers.index('P12_028N')])
        f_10_14 = int(row[headers.index('P12_029N')])
        f_15_17 = int(row[headers.index('P12_030N')])
        
        # 2026 estimated school-age:
        elem = m_under5 + f_under5  # Were <5 in 2020, now 6-10 (elem)
        middle = m_5_9 + f_5_9      # Were 5-9 in 2020, now 11-15 (middle)
        high = m_10_14 + f_10_14    # Were 10-14 in 2020, now 16-20 (HS, some aged out)
        
        total = elem + middle + high
        if total == 0:
            continue
        
        total_elem += elem
        total_ms += middle
        total_hs += high
        
        tracts.append({
            'tract': tract_fips,
            'lat': round(lat, 4),
            'lng': round(lng, 4),
            'elem': elem,
            'middle': middle,
            'high': high,
            'total': total
        })
    
    print(f"\nMcAllen tracts: {len(tracts)}")
    print(f"Est. Elementary students: {total_elem}")
    print(f"Est. Middle school students: {total_ms}")
    print(f"Est. High school students: {total_hs}")
    print(f"Total school-age: {total_elem + total_ms + total_hs}")
    
    result = {
        'tracts': tracts,
        'summary': {
            'elementary': total_elem,
            'middle': total_ms,
            'high': total_hs,
            'total': total_elem + total_ms + total_hs
        }
    }
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))
    
    print(f"Cache: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")

if __name__ == '__main__':
    main()
