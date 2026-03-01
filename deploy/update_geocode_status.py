#!/usr/bin/env python3
"""Update the geocode status file to mark as completed."""
import json

status_file = '/opt/whovoted/data/geocode_registry_status.json'
with open(status_file, 'r') as f:
    status = json.load(f)

status['running'] = False
status['status'] = 'completed'

with open(status_file, 'w') as f:
    json.dump(status, f, indent=2)

print("Status updated to completed")
print(json.dumps(status, indent=2))
