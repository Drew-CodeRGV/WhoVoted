#!/usr/bin/env python3
"""Debug: fetch the Angular app HTML to find JS bundle URLs, then search for API patterns."""
import re
from urllib.request import urlopen, Request

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Fetch the Angular app's index page
req = Request(f'{CIVIX_BASE}/ivis-evr-ui/evr', headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,*/*',
})
html = urlopen(req, timeout=30).read().decode('utf-8')
print(f"HTML length: {len(html)}")
print(f"HTML preview: {html[:500]}")

# Find JS bundle URLs
js_urls = re.findall(r'src="([^"]*\.js[^"]*)"', html)
print(f"\nJS bundles found: {js_urls}")

# Fetch the main bundle and search for API patterns
for js_url in js_urls:
    if 'main' in js_url or 'app' in js_url:
        full_url = js_url if js_url.startswith('http') else f'{CIVIX_BASE}/ivis-evr-ui/{js_url}'
        print(f"\nFetching: {full_url}")
        req2 = Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        js = urlopen(req2, timeout=30).read().decode('utf-8')
        print(f"JS length: {len(js)}")
        
        # Search for API patterns
        for pattern in ['getFile', 'getFileByFormat', 'EVR_STATEWIDE', 'electionDate', 'dateTurnoutId', 'generateReport', 'download', 'csv', 'statewide']:
            matches = [(m.start(), js[max(0,m.start()-80):m.end()+80]) for m in re.finditer(pattern, js, re.IGNORECASE)]
            if matches:
                print(f"\n  '{pattern}' found {len(matches)} times:")
                for pos, ctx in matches[:5]:
                    print(f"    @{pos}: ...{ctx}...")
