#!/usr/bin/env python3
"""
Fix the syntax error in app.py line 1348
"""

# Read the file
with open('/opt/whovoted/backend/app.py', 'r') as f:
    lines = f.readlines()

# Find and remove the problematic line
# Line 1348 (0-indexed: 1347) has: """, params_base + [min_birth_year_18, max_birth_year_18]).fetchone()[0]
# This line doesn't belong - it's a leftover from bad editing

# Find and remove ALL occurrences of the orphaned line
removed_count = 0
i = 0
while i < len(lines):
    if '""", params_base + [min_birth_year_18, max_birth_year_18]).fetchone()[0]' in lines[i]:
        print(f"Found problematic line at {i+1}: {lines[i].strip()}")
        lines.pop(i)
        removed_count += 1
    else:
        i += 1

if removed_count > 0:
    # Write back
    with open('/opt/whovoted/backend/app.py', 'w') as f:
        f.writelines(lines)
    print(f"Fixed! Removed {removed_count} orphaned line(s).")
else:
    print("No problematic lines found.")
