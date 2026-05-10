#!/usr/bin/env python3
"""Seed the elections table with HD-41 runoff election."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO elections (slug, name, description, election_date, price_cents, active)
        VALUES (
            'hd41',
            'Texas House District 41 Runoff',
            'HD-41 runoff election to replace retiring Rep. Bobby Guerra (D). Dem: Julio Salinas vs. Victor "Seby" Haddad. Rep: Sergio Sanchez vs. Gary Groves.',
            '2026-05-26',
            1000,
            1
        )
    """)
    conn.commit()
    conn.close()
    print("✓ Seeded HD-41 election in elections table")

if __name__ == '__main__':
    main()
