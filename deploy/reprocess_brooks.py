#!/usr/bin/env python3
"""Reprocess all 8 Brooks County PDF files through the updated pipeline.

These are mixed-primary files (DEM + REP in one file) — the new auto-split
logic in process_early_vote_roster() will handle splitting by party.
"""
import sys
import os
import glob
import time

sys.path.insert(0, '/opt/whovoted/backend')

from pdf_extractor import extract_pdf_to_csv
from processor import ProcessingJob
from config import Config

upload_dir = '/opt/whovoted/uploads'
output_dir = '/tmp/brooks_reprocess'
os.makedirs(output_dir, exist_ok=True)
pdfs = sorted(glob.glob(os.path.join(upload_dir, '*Voting_History*.pdf')))

print(f"Found {len(pdfs)} Brooks County PDFs to reprocess\n")

for pdf_path in pdfs:
    fname = os.path.basename(pdf_path)
    # Extract the original filename (without UUID prefix)
    original_name = '_'.join(fname.split('_', 1)[1:]) if '_' in fname else fname
    print(f"{'='*70}")
    print(f"Processing: {original_name}")
    print(f"{'='*70}")

    # Step 1: Extract PDF to CSV
    try:
        csv_path = extract_pdf_to_csv(pdf_path, '/tmp/brooks_reprocess')
        if not csv_path:
            print(f"  SKIP: PDF extraction returned no CSV")
            continue
    except Exception as e:
        print(f"  ERROR extracting PDF: {e}")
        continue

    # Step 2: Create processing job
    # primary_party is intentionally left empty — the mixed-primary auto-split
    # will detect DEM/REP in the party column and process each separately
    job = ProcessingJob(
        csv_path=csv_path,
        year='2026',
        county='Brooks',
        election_type='primary',
        election_date='2026-03-03',
        voting_method='early-voting',
        original_filename=original_name,
        primary_party='',  # Empty — triggers mixed-primary auto-split
        max_workers=10,
    )

    # Step 3: Run the job
    try:
        job.run()
        print(f"\n  Status: {job.status}")
        print(f"  Processed: {job.processed_records:,} records")
        print(f"  Geocoded: {job.geocoded_count:,}, Unmatched: {job.failed_count:,}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()

    # Print log
    print(f"\n  --- Job Log ---")
    for msg in job.log_messages[-20:]:
        print(f"  {msg}")
    print()

print("\nAll done.")
