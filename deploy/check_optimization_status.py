#!/usr/bin/env python3
"""Check the status of the optimization script."""
import json
import sys
from pathlib import Path
from datetime import datetime

STATUS_FILE = '/opt/whovoted/data/optimization_status.json'

def main():
    status_path = Path(STATUS_FILE)
    
    if not status_path.exists():
        print("❓ No optimization status found")
        print("   The optimization script hasn't been run yet.")
        sys.exit(0)
    
    try:
        with open(status_path, 'r') as f:
            status = json.load(f)
        
        stage = status.get('stage', 'unknown')
        state = status.get('status', 'unknown')
        message = status.get('message', '')
        
        # Status emoji
        if state == 'running':
            emoji = '⏳'
        elif state == 'completed' or state == 'success':
            emoji = '✅'
        elif state == 'failed':
            emoji = '❌'
        elif state == 'skipped':
            emoji = '⏭️'
        else:
            emoji = '❓'
        
        print(f"\n{emoji} Optimization Status")
        print(f"{'='*50}")
        print(f"Stage:   {stage}")
        print(f"Status:  {state}")
        print(f"Message: {message}")
        
        # Progress bar for districts
        if 'progress' in status:
            progress = status['progress']
            bar_width = 30
            filled = int(bar_width * progress)
            bar = '█' * filled + '░' * (bar_width - filled)
            print(f"Progress: [{bar}] {progress*100:.0f}%")
        
        # Timing info
        if 'started_at' in status:
            started = status['started_at']
            if 'completed_at' in status:
                completed = status['completed_at']
                duration = completed - started
                print(f"Duration: {duration:.1f}s")
            else:
                elapsed = datetime.now().timestamp() - started
                print(f"Elapsed:  {elapsed:.1f}s")
        
        if 'total_time' in status:
            print(f"Total:    {status['total_time']:.1f}s")
        
        # Error details
        if state == 'failed' and 'error' in status:
            print(f"\nError Details:")
            print(status['error'][:500])
        
        print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"❌ Error reading status: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
