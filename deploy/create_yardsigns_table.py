#!/usr/bin/env python3
"""Create the yard_signs table for tracking yard sign observations."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS yard_signs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vuid TEXT NOT NULL,
            election_slug TEXT NOT NULL DEFAULT 'hd41',
            candidate TEXT NOT NULL,
            reported_by TEXT,
            reported_at TEXT DEFAULT (datetime('now')),
            lat REAL,
            lng REAL,
            notes TEXT,
            UNIQUE(vuid, election_slug)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_yardsigns_vuid ON yard_signs(vuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_yardsigns_election ON yard_signs(election_slug)")
    conn.commit()
    conn.close()
    print("✓ Created yard_signs table")

if __name__ == '__main__':
    main()
