#!/usr/bin/env python3
"""Set up the yard sign tracker tables and upload directory."""
import sqlite3, os

DB_PATH = '/opt/whovoted/data/whovoted.db'
UPLOAD_DIR = '/opt/whovoted/uploads/yards'

conn = sqlite3.connect(DB_PATH)

conn.execute("""
    CREATE TABLE IF NOT EXISTS yard_sign_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        photo_url TEXT NOT NULL,
        device_lat REAL NOT NULL,
        device_lng REAL NOT NULL,
        exif_lat REAL,
        exif_lng REAL,
        photo_timestamp TEXT,
        submitted_at TEXT DEFAULT (datetime('now')),
        candidate_identified TEXT,
        candidate_confidence REAL,
        sign_count INTEGER DEFAULT 1,
        ai_description TEXT,
        matched_address TEXT,
        matched_vuid TEXT,
        status TEXT DEFAULT 'pending',
        rejection_reason TEXT,
        verified_at TEXT,
        election_slug TEXT
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS yard_sign_credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        total_submitted INTEGER DEFAULT 0,
        total_verified INTEGER DEFAULT 0,
        credits_earned INTEGER DEFAULT 0,
        last_credit_at TEXT
    )
""")

conn.execute("CREATE INDEX IF NOT EXISTS idx_ysp_user ON yard_sign_photos(user_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_ysp_status ON yard_sign_photos(status)")

conn.commit()
conn.close()

os.makedirs(UPLOAD_DIR, exist_ok=True)
print("✓ yard_sign_photos table created")
print("✓ yard_sign_credits table created")
print(f"✓ Upload dir: {UPLOAD_DIR}")
