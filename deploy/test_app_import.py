#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import os
os.chdir('/opt/whovoted/backend')

try:
    print("Importing app...")
    import app
    print("✓ App imported successfully")
except Exception as e:
    print(f"✗ Error importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
