#!/bin/bash
echo "Testing /api/elections?county=Hidalgo"
echo "======================================"
curl -s "http://127.0.0.1:5000/api/elections?county=Hidalgo" | python3 -c "
import sys, json
data = json.load(sys.stdin)
elections = data.get('elections', [])
print(f'Total elections: {len(elections)}\n')
for i, e in enumerate(elections[:10]):  # First 10
    print(f'{i}. {e.get(\"electionDate\")} | {e.get(\"votingMethod\"):15} | voters: {e.get(\"totalVoters\"):6} | methods: {e.get(\"votingMethods\", [])}')
"
