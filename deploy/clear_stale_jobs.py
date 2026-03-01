#!/usr/bin/env python3
"""Clear all jobs from processing_jobs.json to reset the dashboard."""
import json

JOBS_FILE = '/opt/whovoted/data/processing_jobs.json'

with open(JOBS_FILE, 'w') as f:
    json.dump({}, f)

print("Cleared all jobs from processing_jobs.json")
