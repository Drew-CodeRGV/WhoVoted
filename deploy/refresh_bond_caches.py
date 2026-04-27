#!/usr/bin/env python3
"""Master refresh: rebuilds ALL McAllen ISD Bond 2026 caches."""
import subprocess, sys, time

PYTHON = sys.executable
B = '/opt/whovoted/deploy'

SCRIPTS = [
    (B + '/cache_misdbond2026_voters.py', 'Voter heatmap'),
    (B + '/cache_misdbond2026_nonvoters.py', 'Non-voter heatmap'),
    (B + '/cache_misdbond2026_opportunity.py', 'Opportunity layers'),
    (B + '/cache_misdbond2026_reportcard.py', 'City commission cards'),
    (B + '/cache_misdbond2026_all_campus_reportcards.py', 'School cards'),
    (B + '/cache_misdbond2026_demographics.py', 'Demographics'),
    (B + '/cache_misdbond2026_staff.py', 'Staff matching'),
    (B + '/cache_misdbond2026_gazette.py', 'Gazette'),
]

def main():
    t0 = time.time()
    print('McAllen ISD Bond 2026 - Full Cache Refresh')
    results = []
    for script, label in SCRIPTS:
        print(f'\n--- {label} ---')
        t = time.time()
        r = subprocess.run([PYTHON, script])
        ok = r.returncode == 0
        print(f'{"OK" if ok else "FAIL"} ({time.time()-t:.1f}s)')
        results.append((label, ok))
    print(f'\nDone ({time.time()-t0:.0f}s)')
    for label, ok in results:
        print(f'  {"+" if ok else "X"} {label}')
    return 1 if any(not ok for _, ok in results) else 0

if __name__ == '__main__':
    sys.exit(main())
