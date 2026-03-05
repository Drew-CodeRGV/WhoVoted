#!/usr/bin/env python3
"""Check geocoding accuracy for a specific voter or address."""

import sqlite3
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 check_geocoding_accuracy.py <name_or_vuid>")
        sys.exit(1)
    
    search = sys.argv[1]
    
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # Try to find voter by name or VUID
    print(f'=== Searching for: {search} ===')
    
    # Search by VUID first
    voter = conn.execute('''
        SELECT *
        FROM voters
        WHERE vuid = ?
        LIMIT 1
    ''', (search,)).fetchone()
    
    # If not found, search by name
    if not voter:
        voter = conn.execute('''
            SELECT *
            FROM voters
            WHERE firstname || ' ' || lastname LIKE ?
            LIMIT 1
        ''', (f'%{search}%',)).fetchone()
    
    if not voter:
        print('Voter not found')
        conn.close()
        return
    
    print(f"\nVUID: {voter['vuid']}")
    print(f"Name: {voter['firstname']} {voter['lastname']}")
    print(f"Address: {voter['address'] if voter['address'] else 'N/A'}")
    print(f"City: {voter['city'] if voter['city'] else 'N/A'}, ZIP: {voter['zip'] if voter['zip'] else 'N/A'}")
    print(f"County: {voter['county'] if voter['county'] else 'N/A'}")
    print(f"Coordinates: {voter['lat'] if voter['lat'] else 'N/A'}, {voter['lng'] if voter['lng'] else 'N/A'}")
    print(f"Geocoded: {voter['geocoded']}")
    
    # Check if coordinates look reasonable for Hidalgo County
    lat = voter['lat']
    lng = voter['lng']
    
    if lat and lng:
        # Hidalgo County rough bounds: 26.0-26.8 N, -98.5 to -97.2 W
        if 26.0 <= lat <= 26.8 and -98.5 <= lng <= -97.2:
            print("✓ Coordinates are within Hidalgo County bounds")
        else:
            print("✗ WARNING: Coordinates are OUTSIDE Hidalgo County bounds!")
            print(f"  Expected: 26.0-26.8 N, -98.5 to -97.2 W")
            print(f"  Got: {lat} N, {lng} W")
    
    # Check if voter has voted in 2026
    voted_2026 = conn.execute('''
        SELECT voting_method, party_voted
        FROM voter_elections
        WHERE vuid = ? AND election_date = '2026-03-03'
    ''', (voter['vuid'],)).fetchall()
    
    if voted_2026:
        print(f"\n2026 Voting Record:")
        for v in voted_2026:
            print(f"  - {v['voting_method']}: {v['party_voted']}")
    
    conn.close()

if __name__ == '__main__':
    main()
