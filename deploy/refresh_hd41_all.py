#!/usr/bin/env python3
"""
Master refresh script for HD-41 Runoff Election.
Runs ALL cache rebuilds in the correct order after new data is imported.

Usage:
  python3 deploy/refresh_hd41_all.py
"""
import subprocess, sys, time

PYTHON = sys.executable
BASE = '/opt/whovoted/deploy'

CACHE_SCRIPTS = [
    (f'{BASE}/cache_hd41_voters.py', 'Runoff voter heatmap + search'),
    (f'{BASE}/cache_hd41_march_primary.py', 'March primary results + mobilization targets'),
    (f'{BASE}/cache_hd41_nonvoters.py', 'Non-voter heatmap'),
    (f'{BASE}/cache_hd41_reportcard.py', 'Dual-race precinct report cards'),
    (f'{BASE}/cache_hd41_demographics.py', 'Demographics'),
    (f'{BASE}/cache_hd41_gazette.py', 'Gazette'),
]

def run(script, label=None):
    name = label or script.split('/')[-1]
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    t = time.time()
    r = subprocess.run([PYTHON, script])
    s = '✓' if r.returncode == 0 else '✗'
    print(f"  {s} {name} ({time.time()-t:.1f}s)")
    return r.returncode == 0

def main():
    t0 = time.time()
    print("=" * 60)
    print("  HD-41 Runoff Election - Full Cache Refresh")
    print("  Dem: Salinas vs Haddad | Rep: Sanchez vs Groves")
    print("=" * 60)

    results = []
    for script, label in CACHE_SCRIPTS:
        results.append((label, run(script, label)))

    print(f"\n{'='*60}")
    print(f"  DONE ({time.time()-t0:.0f}s)")
    for label, ok in results:
        print(f"  {'✓' if ok else '✗'} {label}")
    return 1 if any(not ok for _, ok in results) else 0

if __name__ == '__main__':
    sys.exit(main())
