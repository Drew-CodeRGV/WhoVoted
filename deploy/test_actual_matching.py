#!/usr/bin/env python3
"""
Test the actual matching logic with real data
"""
import sqlite3
import re

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

class PrecinctNormalizer:
    @staticmethod
    def normalize(precinct, county=None):
        if not precinct:
            return set()
        
        p = str(precinct).strip().upper()
        normalized = set()
        normalized.add(p)
        no_space = p.replace(' ', '')
        normalized.add(no_space)
        
        numbers = re.findall(r'\d+', p)
        if numbers:
            normalized.add(''.join(numbers))
            for num in numbers:
                normalized.add(num)
                normalized.add(num.lstrip('0') or '0')
                normalized.add(num.zfill(4))
        
        for prefix in ['PCT', 'PRECINCT', 'PRE', 'P', 'S', 'E', 'W', 'N']:
            if p.startswith(prefix):
                suffix = p[len(prefix):].strip()
                if suffix:
                    normalized.add(suffix)
                    normalized.update(PrecinctNormalizer.normalize(suffix))
        
        if '.' in p:
            no_decimal = p.replace('.', '')
            normalized.add(no_decimal)
            parts = p.split('.')
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                major = parts[0].strip()
                minor = parts[1].strip()
                normalized.add(f"{major}{minor.zfill(2)}")
                normalized.add(f"{major.zfill(2)}{minor.zfill(2)}")
        
        if '-' in p:
            no_hyphen = p.replace('-', '')
            normalized.add(no_hyphen)
            parts = p.split('-')
            if len(parts) == 2:
                normalized.add(f"{parts[0]}{parts[1].zfill(2)}")
        
        if '/' in p:
            no_slash = p.replace('/', '')
            normalized.add(no_slash)
        
        return normalized


conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("ACTUAL MATCHING TEST")
print("=" * 80)

# Get a sample Hidalgo voter
cursor.execute("""
    SELECT ve.id, ve.vuid, ve.precinct, v.county
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct = '151'
    LIMIT 1
""", (ELECTION_DATE,))

voter = cursor.fetchone()

if voter:
    print(f"\nTest voter:")
    print(f"  VUID: {voter['vuid']}")
    print(f"  Precinct: '{voter['precinct']}'")
    print(f"  County: {voter['county']}")
    
    # Generate variants
    variants = PrecinctNormalizer.normalize(voter['precinct'], voter['county'])
    print(f"\n  Generated variants: {sorted(variants)}")
    
    # Try to match each variant
    print(f"\n  Trying to match each variant:")
    found = False
    for variant in variants:
        cursor.execute("""
            SELECT congressional_district
            FROM precinct_normalized
            WHERE county = ? AND normalized_precinct = ?
            LIMIT 1
        """, (voter['county'], variant))
        
        result = cursor.fetchone()
        if result and result[0]:
            print(f"    '{variant}' → MATCH! District: {result[0]}")
            found = True
            break
        else:
            print(f"    '{variant}' → no match")
    
    if found:
        print(f"\n  ✓ Should have been assigned to district")
    else:
        print(f"\n  ✗ No match found")
        
        # Debug: check what's in the table
        print(f"\n  Debug: Checking normalized table directly...")
        cursor.execute("""
            SELECT normalized_precinct, congressional_district
            FROM precinct_normalized
            WHERE county = 'Hidalgo'
            AND normalized_precinct IN ('151', '0151')
        """)
        
        for row in cursor.fetchall():
            print(f"    Found: '{row['normalized_precinct']}' → District {row['congressional_district']}")

conn.close()
