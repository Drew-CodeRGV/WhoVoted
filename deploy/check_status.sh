#!/bin/bash
# Quick status checker - run this to see optimization progress

PYTHON="/opt/whovoted/venv/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run in watch mode if requested
if [ "$1" == "watch" ]; then
    while true; do
        clear
        $PYTHON "$SCRIPT_DIR/optimization_status.py"
        echo "Refreshing every 2 seconds... (Ctrl+C to stop)"
        sleep 2
    done
else
    $PYTHON "$SCRIPT_DIR/optimization_status.py"
fi
