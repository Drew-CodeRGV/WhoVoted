#!/usr/bin/env python3
"""Test the DB-driven endpoints by calling database functions directly."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

db.init_db()

print("=== Election Datasets ===")
datasets = db.get_election_datasets()
print(f"Count: {len(datasets)}")
for d in datasets:
    print(f"  {d['election_date']} | {d['party_voted']:12s} | {d['voting_method']:15s} | "
          f"total={d['total_voters']:>6,} geo={d['geocoded_count']:>6,} ungeo={d['ungeocoded_count']:>6,} | {d['county']}")

print("\n=== Election Summary ===")
summary = db.get_election_summary()
for k, v in summary.items():
    print(f"  {k}: {v}")
