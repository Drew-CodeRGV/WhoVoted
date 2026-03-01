#!/usr/bin/env python3
"""Determine which counties fall within the new TX-15 (PlanC2333)."""
import json

def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_feature(lng, lat, feature):
    geom = feature['geometry']
    if geom['type'] == 'Polygon':
        return point_in_polygon([lng, lat], geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon':
        return any(point_in_polygon([lng, lat], poly[0]) for poly in geom['coordinates'])
    return False

districts = json.load(open('/opt/whovoted/public/data/districts.json'))
tx15 = [f for f in districts['features']
        if f['properties'].get('district_id') == 'TX-15'][0]

# RGV and surrounding county seats / major cities with coordinates
# Testing a grid of points across South Texas
counties = [
    # County name, city, lng, lat
    ('Hidalgo', 'Edinburg', -98.1631, 26.3017),
    ('Hidalgo', 'McAllen', -98.2300, 26.2034),
    ('Hidalgo', 'Mission', -98.3253, 26.2159),
    ('Hidalgo', 'Pharr', -98.1836, 26.1950),
    ('Hidalgo', 'Weslaco', -97.9908, 26.1595),
    ('Hidalgo', 'Mercedes', -97.9139, 26.1498),
    ('Hidalgo', 'Donna', -98.0517, 26.1703),
    ('Hidalgo', 'San Juan', -98.1553, 26.1892),
    ('Hidalgo', 'Alamo', -98.1231, 26.1842),
    ('Hidalgo', 'Elsa', -97.9931, 26.2931),
    ('Hidalgo', 'Edcouch', -97.9614, 26.2939),
    ('Hidalgo', 'La Joya', -98.4817, 26.2467),
    ('Hidalgo', 'Palmview', -98.3706, 26.2339),
    ('Hidalgo', 'Penitas', -98.4428, 26.2297),
    ('Hidalgo', 'Sullivan City', -98.5636, 26.2753),
    ('Hidalgo', 'Hidalgo city', -98.2631, 26.1003),
    ('Cameron', 'Brownsville', -97.4975, 25.9017),
    ('Cameron', 'Harlingen', -97.6961, 26.1906),
    ('Cameron', 'San Benito', -97.6311, 26.1328),
    ('Cameron', 'Los Fresnos', -97.4764, 26.0714),
    ('Cameron', 'La Feria', -97.8231, 26.1581),
    ('Cameron', 'Port Isabel', -97.2086, 26.0731),
    ('Starr', 'Rio Grande City', -98.8203, 26.3797),
    ('Starr', 'Roma', -99.0156, 26.4050),
    ('Brooks', 'Falfurrias', -98.1442, 27.2267),
    ('Jim Hogg', 'Hebbronville', -98.6831, 27.3067),
    ('Zapata', 'Zapata', -99.2714, 26.9069),
    ('Webb', 'Laredo', -99.5075, 27.5064),
    ('Kenedy', 'Sarita', -97.7892, 27.2217),
    ('Willacy', 'Raymondville', -97.7831, 26.4817),
    ('Jim Wells', 'Alice', -98.0697, 27.7522),
    ('Nueces', 'Corpus Christi', -97.3964, 27.8006),
    ('Kleberg', 'Kingsville', -97.8561, 27.5159),
    ('Duval', 'San Diego TX', -98.2386, 27.7639),
    ('Live Oak', 'George West', -98.1175, 28.3325),
    ('McMullen', 'Tilden', -98.5492, 28.4614),
    ('Bee', 'Beeville', -97.7486, 28.4011),
    ('San Patricio', 'Sinton', -97.5094, 28.0367),
    ('Refugio', 'Refugio', -97.2753, 28.3053),
    ('Aransas', 'Rockport', -97.0544, 28.0206),
    ('Calhoun', 'Port Lavaca', -96.6264, 28.6150),
    ('Victoria', 'Victoria', -96.9853, 28.8053),
    ('Goliad', 'Goliad', -97.3883, 28.6683),
    ('DeWitt', 'Cuero', -97.2892, 29.0939),
    ('Lavaca', 'Hallettsville', -96.9411, 29.4439),
    ('Jackson', 'Edna', -96.6461, 28.9786),
    ('Matagorda', 'Bay City', -95.9694, 28.9828),
    ('Wharton', 'Wharton', -96.1028, 29.3117),
]

print("Counties in new TX-15 (PlanC2333):")
in_district = {}
for county, city, lng, lat in counties:
    if point_in_feature(lng, lat, tx15):
        if county not in in_district:
            in_district[county] = []
        in_district[county].append(city)

for county in sorted(in_district.keys()):
    cities = ', '.join(in_district[county])
    print(f"  {county} County — {cities}")

print(f"\nTotal: {len(in_district)} counties")

# Also check which are NOT in TX-15
print("\nNOT in TX-15:")
not_in = {}
for county, city, lng, lat in counties:
    if not point_in_feature(lng, lat, tx15):
        if county not in not_in:
            not_in[county] = []
        not_in[county].append(city)
for county in sorted(not_in.keys()):
    cities = ', '.join(not_in[county])
    print(f"  {county} County — {cities}")
