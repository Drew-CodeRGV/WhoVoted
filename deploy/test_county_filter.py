#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted')
from backend import database as db

# Test without county filter
voters = db.get_voters_at_location(26.2034, -98.2300, '2026-03-03', 'combined', None)
print(f'Without county filter: {len(voters)} voters')
if voters:
    print(f'First voter county: {voters[0].get("county")}')
    print(f'First voter address: {voters[0].get("address")}')

# Test with county filter
voters_filtered = db.get_voters_at_location(26.2034, -98.2300, '2026-03-03', 'combined', ['Hidalgo'])
print(f'With Hidalgo filter: {len(voters_filtered)} voters')
