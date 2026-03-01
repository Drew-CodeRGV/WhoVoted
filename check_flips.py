import json
import sys

# Check 2026 Republican data
with open('/opt/whovoted/data/map_data_Hidalgo_2026_primary_republican_20260223.json') as f:
    data = json.load(f)
features = data.get('features', [])
print("=== 2026 REP ===")
print("Total features:", len(features))
flipped = [f for f in features if f.get('properties', {}).get('flipped_from')]
print("With flipped_from:", len(flipped))
if flipped:
    print("Sample flipped:", json.dumps(flipped[0]['properties'], indent=2))

# Check properties keys
if features:
    props = features[0].get('properties', {})
    print("Property keys:", list(props.keys()))
    # Check for any flip-related fields
    for key in props.keys():
        if 'flip' in key.lower() or 'party' in key.lower() or 'prev' in key.lower():
            print("  Found relevant key:", key, "=", props[key])

print()

# Check 2026 Democratic data
with open('/opt/whovoted/data/map_data_Hidalgo_2026_primary_democratic_20260223.json') as f:
    data = json.load(f)
features = data.get('features', [])
print("=== 2026 DEM ===")
print("Total features:", len(features))
flipped = [f for f in features if f.get('properties', {}).get('flipped_from')]
print("With flipped_from:", len(flipped))
if flipped:
    print("Sample flipped:", json.dumps(flipped[0]['properties'], indent=2))

if features:
    props = features[0].get('properties', {})
    print("Property keys:", list(props.keys()))
    for key in props.keys():
        if 'flip' in key.lower() or 'party' in key.lower() or 'prev' in key.lower():
            print("  Found relevant key:", key, "=", props[key])

print()

# Compare: check 2024 data to see if it has flip data
try:
    with open('/opt/whovoted/data/map_data_Hidalgo_2024_primary_democratic_20240305.json') as f:
        data = json.load(f)
    features = data.get('features', [])
    print("=== 2024 DEM (for comparison) ===")
    print("Total features:", len(features))
    flipped = [f for f in features if f.get('properties', {}).get('flipped_from')]
    print("With flipped_from:", len(flipped))
    if features:
        props = features[0].get('properties', {})
        print("Property keys:", list(props.keys()))
        for key in props.keys():
            if 'flip' in key.lower() or 'party' in key.lower() or 'prev' in key.lower():
                print("  Found relevant key:", key, "=", props[key])
    if flipped:
        print("Sample flipped:", json.dumps(flipped[0]['properties'], indent=2))
except Exception as e:
    print("Error reading 2024 data:", e)
