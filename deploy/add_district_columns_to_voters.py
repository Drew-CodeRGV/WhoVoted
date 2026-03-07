#!/usr/bin/env python3
"""Add district columns to voters table if they don't exist."""

import sqlite3

db_path = "data/whovoted.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current columns
cursor.execute("PRAGMA table_info(voters)")
columns = {row[1] for row in cursor.fetchall()}

print("Current columns in voters table:")
for col in sorted(columns):
    print(f"  - {col}")

# Add missing district columns
columns_to_add = [
    ('state_senate_district', 'TEXT'),
    ('state_house_district', 'TEXT'),
]

# Check if congressional_district exists, if not add it too
if 'congressional_district' not in columns:
    columns_to_add.insert(0, ('congressional_district', 'TEXT'))

print("\nAdding missing district columns...")
for col_name, col_type in columns_to_add:
    if col_name not in columns:
        try:
            cursor.execute(f"ALTER TABLE voters ADD COLUMN {col_name} {col_type}")
            print(f"  ✓ Added {col_name}")
        except sqlite3.OperationalError as e:
            print(f"  ⚠ {col_name}: {e}")
    else:
        print(f"  - {col_name} already exists")

conn.commit()

# Verify
cursor.execute("PRAGMA table_info(voters)")
columns_after = {row[1] for row in cursor.fetchall()}

print("\nDistrict columns in voters table:")
for col in sorted(columns_after):
    if 'district' in col.lower():
        print(f"  ✓ {col}")

conn.close()
print("\n✓ Complete")
