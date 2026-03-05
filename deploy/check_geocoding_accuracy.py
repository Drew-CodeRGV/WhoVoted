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
        SELECT v.*, es.lat, es.lng, es.address as geocoded_address
        FROM voters v
        LEFT JOIN election_summary es ON v.vuid = es.vuid
        WHERE v.vuid = ?
        LIMIT 1
    ''', (search,)).fetchone()
    
    # If not found, search by name
    if not voter:
        voter = conn.execute('''
            SELECT v.*, es.lat, es.lng, es.address as geocoded_address
            FROM voters v
            LEFT JOIN election_summary es ON v.vuid = es.vuid
            WHERE v.firstname || ' ' || v.lastname LIKE ?
            LIMIT 1
        ''', (f'%{search}%',)).fetchone()
    
    if not voter:
        print('Voter not found')
        conn.close()
        return
    
    print(f"\nVUID: {voter['vuid']}")
    print(f"Name: {voter['firstname']} {voter['lastname']}")
    print(f"Address (voter record): {voter.get('address', 'N/A')}")
    print(f"Address (geocoded): {voter.get('geocoded_address', 'N/A')}")
    print(f"Coordinates: {voter.get('lat', 'N/A')}, {voter.get('lng', 'N/A')}")
    
    # Check if coordinates look reasonable for Hidalgo County
    lat = voter.get('lat')
    lng = voter.get('lng')
    
    if lat and lng:
        # Hidalgo County rough bounds: 26.0-26.8 N, -98.5 to -97.2 W
        if 26.0 <= lat <= 26.8 and -98.5 <= lng <= -97.2:
            print("✓ Coordinates are within Hidalgo County bounds")
        else:
            print("✗ WARNING: Coordinates are OUTSIDE Hidalgo County bounds!")
            print(f"  Expected: 26.0-26.8 N, -98.5 to -97.2 W")
            print(f"  Got: {lat} N, {lng} W")
    
    # Check geocoding quality if available
    quality = conn.execute('''
        SELECT geocode_quality, geocode_source
        FROM election_summary
        WHERE vuid = ?
        LIMIT 1
    ''', (voter['vuid'],)).fetchone()
    
    if quality:
        print(f"\nGeocoding Quality: {quality.get('geocode_quality', 'N/A')}")
        print(f"Geocoding Source: {quality.get('geocode_source', 'N/A')}")
    
    conn.close()

if __name__ == '__main__':
    main()
