#!/bin/bash
# Start batch geocode in background with proper env
export PATH="/opt/whovoted/venv/bin:$PATH"
cd /opt/whovoted

# Source env vars
set -a
source /opt/whovoted/.env
set +a

# Kill any existing batch geocode process
pkill -f "batch_geocode_aws.py" 2>/dev/null || true
sleep 1

# Start in background
nohup /opt/whovoted/venv/bin/python3 -u /opt/whovoted/deploy/batch_geocode_aws.py --workers 20 --batch-size 200 >> /opt/whovoted/logs/batch_geocode_stdout.log 2>&1 &
PID=$!
echo $PID > /opt/whovoted/data/batch_geocode_pid.txt
echo "Started batch geocode PID: $PID"
sleep 2
# Verify it's running
if ps -p $PID > /dev/null 2>&1; then
    echo "Process is running"
else
    echo "Process DIED - check logs:"
    tail -20 /opt/whovoted/logs/batch_geocode_stdout.log
    tail -20 /opt/whovoted/logs/batch_geocode.log
fi
