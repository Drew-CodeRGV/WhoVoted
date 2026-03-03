#!/usr/bin/env python3
"""Check Brooks County age data."""

import sqlite3

def check_brooks_data():
    conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
    
    # Check if Brooks has birth_year data
    sample = conn.execute("""
        SELECT v.vuid, v.birth_year, v.sex, ve.party_voted
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Brooks' AND ve.election_date = '2026-03-03'
        LIMIT 20
    """).fetchall()
    
    print("Brooks County sample records:")
    birth_years_found = 0
    for row in sample:
        print(f"  VUID: {row[0]}, Birth: {row[1]}, Sex: {row[2]}, Party: {row[3]}")
        if row[1] and row[1] > 0:
            birth_years_found += 1
    
    print(f"\nRecords with birth_year: {birth_years_found}/{len(sample)}")
    
    # Count total with birth years
    total_with_birth = conn.execute("""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Brooks' AND ve.election_date = '2026-03-03'
          AND v.birth_year IS NOT NULL AND v.birth_year > 0
    """).fetchone()[0]
    
    total = conn.execute("""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Brooks' AND ve.election_date = '2026-03-03'
    """).fetchone()[0]
    
    print(f"\nTotal Brooks voters: {total}")
    print(f"With birth_year: {total_with_birth} ({100*total_with_birth/total if total else 0:.1f}%)")
    
    conn.close()

if __name__ == '__main__':
    check_brooks_data()
