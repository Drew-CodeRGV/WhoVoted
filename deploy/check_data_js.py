#!/usr/bin/env python3
"""Check what loadMapData looks like on the server."""
with open('/opt/whovoted/public/data.js', 'r') as f:
    content = f.read()

# Find the loadMapData function and print the default dataset selection
import re
match = re.search(r'(// Load the most recent dataset.*?No datasets found.*?\})', content, re.DOTALL)
if match:
    print("Default dataset selection code:")
    print(match.group(1))
else:
    # Try finding by line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'most recent dataset' in line.lower() or 'defaultIndex' in line or 'defaultDataset' in line:
            start = max(0, i-1)
            end = min(len(lines), i+15)
            print(f"Lines {start+1}-{end+1}:")
            for j in range(start, end):
                print(f"  {j+1}: {lines[j]}")
            print()
