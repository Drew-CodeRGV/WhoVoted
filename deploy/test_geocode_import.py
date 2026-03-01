#!/usr/bin/env python3
import sys
print("Python:", sys.version)
print("Testing imports...")

try:
    import sqlite3
    print("sqlite3 OK")
except Exception as e:
    print(f"sqlite3 FAIL: {e}")

try:
    import boto3
    print("boto3 OK")
except Exception as e:
    print(f"boto3 FAIL: {e}")

try:
    from dotenv import load_dotenv
    print("dotenv OK")
except Exception as e:
    print(f"dotenv FAIL: {e}")

try:
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError
    print("botocore OK")
except Exception as e:
    print(f"botocore FAIL: {e}")

# Now try running the actual script
print("\nTrying to import batch_geocode_aws...")
sys.path.insert(0, '/opt/whovoted/deploy')
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("batch_geocode_aws", "/opt/whovoted/deploy/batch_geocode_aws.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("Import successful!")
    print("Has run():", hasattr(mod, 'run'))
except Exception as e:
    print(f"Import FAIL: {e}")
    import traceback
    traceback.print_exc()
