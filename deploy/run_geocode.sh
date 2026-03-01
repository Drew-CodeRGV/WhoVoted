#!/bin/bash
cd /opt/whovoted
echo "Launching batch geocode in background..."
nohup /opt/whovoted/venv/bin/python3 -u /opt/whovoted/deploy/batch_geocode_aws.py --workers 20 --batch-size 500 > /opt/whovoted/logs/batch_geocode_output.log 2>&1 &
echo "PID: $!"
echo "Logs: /opt/whovoted/logs/batch_geocode_output.log"
echo "Status: /opt/whovoted/data/batch_geocode_status.json"
