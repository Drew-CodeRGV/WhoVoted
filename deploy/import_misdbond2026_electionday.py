#!/usr/bin/env python3
"""
Import McAllen ISD Bond 2026 election day rosters.
Election day: May 10, 2026

This script handles election day voter data which may come from:
1. Hidalgo County election day roster PDF/Excel (same format as EV roster)
2. Manual VUID list

Usage:
  python3 deploy/import_misdbond2026_electionday.py <url_or_file>
  python3 deploy/import_misdbond2026_electionday.py  # uses default URL if set

After import, automatically rebuilds all caches.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from import_misdbond2026_roster import download_roster, parse_roster_pdf, _import_vuids

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-05-10'

# Update this URL when Hidalgo County posts the election day roster
# Format will likely be similar to EV roster
ELECTIONDAY_URL = None  # Set when available

def main():
    url_or_file = sys.argv[1] if len(sys.argv) > 1 else ELECTIONDAY_URL
    
    if not url_or_file:
        print("Usage: python3 import_misdbond2026_electionday.py <url_or_file>")
        print("No election day roster URL configured yet.")
        print("Set ELECTIONDAY_URL in this script or pass URL as argument.")
        return 1
    
    print("=" * 60)
    print("  McAllen ISD Bond 2026 - Election Day Import")
    print("=" * 60)
    
    if url_or_file.startswith('http'):
        content = download_roster(url_or_file)
    else:
        with open(url_or_file, 'rb') as f:
            content = f.read()
    
    vuids = parse_roster_pdf(content)
    if not vuids:
        print("No VUIDs extracted")
        return 1
    
    print(f"Found {len(vuids)} election day VUIDs")
    imported = _import_vuids(vuids, 'election-day', 'hidalgo-electionday-roster')
    
    if imported > 0:
        print(f"\nImported {imported} election day voters")
        print("Rebuilding all caches...")
        import subprocess
        subprocess.run([sys.executable, '/opt/whovoted/deploy/refresh_bond_caches.py'])
    else:
        print("No new election day voters to import")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
