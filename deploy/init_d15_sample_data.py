#!/usr/bin/env python3
"""Initialize District 15 election results table with sample data for testing."""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Get database path - use relative path from script location
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR.parent / 'data' / 'whovoted.db'

def init_sample_data():
    """Create table and insert sample election results."""
    if not DB_PATH.exists():
        print(f"✗ Database not found at: {DB_PATH}")
        print(f"  Please ensure the database exists first.")
        sys.exit(1)
    
    print(f"Using database: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    
    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS election_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            election_date TEXT NOT NULL,
            district TEXT NOT NULL,
            county TEXT NOT NULL,
            precinct TEXT NOT NULL,
            dem_votes INTEGER DEFAULT 0,
            rep_votes INTEGER DEFAULT 0,
            updated_at TEXT,
            UNIQUE(election_date, district, county, precinct)
        )
    """)
    
    # Sample data for testing
    election_date = '2026-03-03'
    updated_at = datetime.now().isoformat()
    
    sample_data = [
        # Hidalgo County precincts
        ('Hidalgo', '101', 450, 320),
        ('Hidalgo', '102', 380, 290),
        ('Hidalgo', '103', 520, 410),
        ('Hidalgo', '104', 290, 380),
        ('Hidalgo', '105', 410, 350),
        ('Hidalgo', '106', 380, 420),
        ('Hidalgo', '107', 490, 380),
        ('Hidalgo', '108', 350, 310),
        # Cameron County precincts
        ('Cameron', '201', 610, 450),
        ('Cameron', '202', 540, 490),
        ('Cameron', '203', 470, 520),
        ('Cameron', '204', 580, 460),
        ('Cameron', '205', 520, 510),
        # Willacy County precincts
        ('Willacy', '301', 180, 220),
        ('Willacy', '302', 150, 190),
        ('Willacy', '303', 170, 200),
    ]
    
    for county, precinct, dem, rep in sample_data:
        conn.execute("""
            INSERT OR REPLACE INTO election_results 
            (election_date, district, county, precinct, dem_votes, rep_votes, updated_at)
            VALUES (?, '15', ?, ?, ?, ?, ?)
        """, [election_date, county, precinct, dem, rep, updated_at])
    
    conn.commit()
    
    # Verify data
    result = conn.execute("""
        SELECT 
            COUNT(*) as total_precincts,
            SUM(dem_votes) as total_dem,
            SUM(rep_votes) as total_rep
        FROM election_results
        WHERE district = '15' AND election_date = ?
    """, [election_date]).fetchone()
    
    print(f"✓ Initialized election_results table")
    print(f"✓ Inserted {result[0]} precincts")
    print(f"✓ Total votes: {result[1]:,} Democratic, {result[2]:,} Republican")
    
    conn.close()

if __name__ == '__main__':
    init_sample_data()
