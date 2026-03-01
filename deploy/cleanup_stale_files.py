#!/usr/bin/env python3
"""Clean up stale GeoJSON files with wrong dates."""
import os, glob

for base_dir in ['/opt/whovoted/data', '/opt/whovoted/public/data']:
    for pattern in ['*20260223*', '*20260224*']:
        for f in glob.glob(os.path.join(base_dir, pattern)):
            print(f"Removing: {f}")
            os.remove(f)

# Verify what's left
print("\nRemaining 2026 files in public/data:")
for f in sorted(glob.glob("/opt/whovoted/public/data/*2026*")):
    print(f"  {os.path.basename(f)}")
