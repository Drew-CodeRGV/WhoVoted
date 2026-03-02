#!/usr/bin/env python3
"""Check what statewide data we have."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("Statewide data availability:")
print("2022:", conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01'").fetchone()[0], "votes")
print("2024:", conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05'").fetchone()[0], "votes")
print("2026:", conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0], "votes")

conn.close()
