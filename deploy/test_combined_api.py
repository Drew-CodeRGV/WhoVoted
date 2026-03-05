#!/usr/bin/env python3
"""Test the /api/elections endpoint to see if combined datasets are being returned"""
import requests
import json

url = 'https://politiquera.com/api/elections?county=Hidalgo'

print('Testing /api/elections endpoint...')
print(f'URL: {url}\n')

response = requests.get(url)
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    
    if data.get('success'):
        elections = data.get('elections', [])
        print(f'\nTotal datasets returned: {len(elections)}\n')
        
        print('Datasets:')
        print('=' * 80)
        for i, election in enumerate(elections):
            print(f"\n{i+1}. {election.get('electionDate')} - {election.get('votingMethod')}")
            print(f"   Year: {election.get('electionYear')}")
            print(f"   Type: {election.get('electionType')}")
            print(f"   Total Voters: {election.get('totalVoters'):,}")
            
            if election.get('votingMethod') == 'combined':
                print(f"   ✓ COMBINED DATASET")
                print(f"   Methods included: {election.get('votingMethods')}")
                if 'methodBreakdown' in election:
                    print(f"   Method breakdown:")
                    for method, stats in election['methodBreakdown'].items():
                        print(f"     - {method}: {stats['totalVoters']:,} voters")
            else:
                print(f"   Individual dataset: {election.get('votingMethod')}")
    else:
        print('API returned success=false')
        print(json.dumps(data, indent=2))
else:
    print(f'Error: {response.text}')
