#!/bin/bash
cd /opt/whovoted
echo "Starting batch geocode dry run..."
/opt/whovoted/venv/bin/python3 -u /opt/whovoted/deploy/batch_geocode_aws.py --dry-run 2>&1
RC=$?
echo "EXIT CODE: $RC"
echo "--- Status file ---"
cat /opt/whovoted/data/batch_geocode_status.json 2>/dev/null || echo "No status file"
