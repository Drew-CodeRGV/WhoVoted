#!/usr/bin/env python3
"""Check the list-datasets API response for 2026 datasets."""
import json
import urllib.request

resp = urllib.request.urlopen('http://localhost:5000/admin/list-datasets')
data = json.loads(resp.read())

for d in data['datasets']:
    if d['year'] == '2026':
        print(json.dumps({
            'primaryParty': d.get('primaryParty'),
            'totalAddresses': d.get('totalAddresses'),
            'rawVoterCount': d.get('rawVoterCount'),
            'isCumulative': d.get('isCumulative'),
            'votingMethod': d.get('votingMethod'),
            'electionDate': d.get('electionDate'),
            'mapDataFile': d.get('mapDataFile'),
        }, indent=2))
        print('---')
