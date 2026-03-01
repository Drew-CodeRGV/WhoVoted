#!/usr/bin/env python3
"""
Shared status tracking for optimization scripts.
Writes JSON status file that can be monitored in real-time.
"""
import json
import time
from pathlib import Path
from datetime import datetime

STATUS_FILE = '/opt/whovoted/data/optimization_status.json'

class OptimizationStatus:
    """Track optimization progress with real-time status updates."""
    
    def __init__(self, script_name):
        self.script_name = script_name
        self.start_time = time.time()
        self.status = {
            'script': script_name,
            'status': 'starting',
            'stage': 'initialization',
            'progress': 0.0,
            'message': 'Starting...',
            'started_at': datetime.now().isoformat(),
            'elapsed_seconds': 0,
            'steps': []
        }
        self.write()
    
    def update(self, stage, message, progress=None, status='running'):
        """Update status with current stage and progress."""
        self.status['stage'] = stage
        self.status['message'] = message
        self.status['status'] = status
        self.status['elapsed_seconds'] = int(time.time() - self.start_time)
        
        if progress is not None:
            self.status['progress'] = progress
        
        # Add to steps log
        self.status['steps'].append({
            'stage': stage,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'elapsed': self.status['elapsed_seconds']
        })
        
        self.write()
    
    def complete(self, message='Completed successfully'):
        """Mark optimization as complete."""
        self.status['status'] = 'completed'
        self.status['message'] = message
        self.status['progress'] = 1.0
        self.status['elapsed_seconds'] = int(time.time() - self.start_time)
        self.status['completed_at'] = datetime.now().isoformat()
        self.write()
    
    def error(self, message, error_details=None):
        """Mark optimization as failed."""
        self.status['status'] = 'failed'
        self.status['message'] = message
        self.status['elapsed_seconds'] = int(time.time() - self.start_time)
        self.status['failed_at'] = datetime.now().isoformat()
        
        if error_details:
            self.status['error'] = str(error_details)
        
        self.write()
    
    def write(self):
        """Write status to JSON file."""
        try:
            Path(STATUS_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not write status file: {e}")

def read_status():
    """Read current optimization status."""
    try:
        if Path(STATUS_FILE).exists():
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

def format_status_display(status):
    """Format status for terminal display."""
    if not status:
        return "❓ No optimization running"
    
    # Status emoji
    status_map = {
        'starting': '🔄',
        'running': '⏳',
        'completed': '✅',
        'failed': '❌',
        'skipped': '⏭️'
    }
    emoji = status_map.get(status.get('status', 'unknown'), '❓')
    
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append(f"{emoji} Optimization Status: {status.get('script', 'Unknown')}")
    lines.append("=" * 70)
    lines.append(f"Stage:    {status.get('stage', 'unknown')}")
    lines.append(f"Status:   {status.get('status', 'unknown')}")
    lines.append(f"Message:  {status.get('message', '')}")
    
    # Progress bar
    progress = status.get('progress', 0)
    if progress > 0:
        bar_width = 40
        filled = int(bar_width * progress)
        bar = '█' * filled + '░' * (bar_width - filled)
        lines.append(f"Progress: [{bar}] {progress*100:.0f}%")
    
    # Timing
    elapsed = status.get('elapsed_seconds', 0)
    if elapsed > 0:
        mins = elapsed // 60
        secs = elapsed % 60
        if mins > 0:
            lines.append(f"Elapsed:  {mins}m {secs}s")
        else:
            lines.append(f"Elapsed:  {secs}s")
    
    # Recent steps (last 5)
    steps = status.get('steps', [])
    if steps:
        lines.append("")
        lines.append("Recent Steps:")
        for step in steps[-5:]:
            elapsed = step.get('elapsed', 0)
            lines.append(f"  [{elapsed:4d}s] {step.get('stage', '')}: {step.get('message', '')}")
    
    # Error details
    if status.get('status') == 'failed' and 'error' in status:
        lines.append("")
        lines.append("Error Details:")
        error = status['error']
        if len(error) > 300:
            error = error[:300] + "..."
        lines.append(error)
    
    lines.append("=" * 70)
    lines.append("")
    
    return "\n".join(lines)

if __name__ == '__main__':
    # Display current status
    status = read_status()
    print(format_status_display(status))
