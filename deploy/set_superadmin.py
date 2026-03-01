#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
email = 'drew@drewlentz.com'
# Check if user exists
row = conn.execute("SELECT id, email, role FROM users WHERE email = ?", (email,)).fetchone()
if row:
    conn.execute("UPDATE users SET role = 'superadmin' WHERE email = ?", (email,))
    conn.commit()
    print(f"Updated {email} to superadmin (was {row[2]})")
else:
    conn.execute("INSERT INTO users (email, role, created_at) VALUES (?, 'superadmin', datetime('now'))", (email,))
    conn.commit()
    print(f"Created {email} as superadmin")
conn.close()
