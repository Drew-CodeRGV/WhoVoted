#!/usr/bin/env python3
"""Test that the updated ePulse regex handles both DOB and no-DOB formats."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
from pdf_extractor import extract_pdf_to_csv
import os
import glob

upload_dir = '/opt/whovoted/uploads'
pdfs = sorted(glob.glob(os.path.join(upload_dir, '*Voting_History*.pdf')))

print(f"Found {len(pdfs)} Brooks County PDFs\n")
for pdf in pdfs:
    fname = os.path.basename(pdf)
    print(f"--- {fname} ---")
    try:
        csv_path = extract_pdf_to_csv(pdf, '/tmp')
        if csv_path:
            with open(csv_path) as f:
                lines = f.readlines()
            print(f"  Rows: {len(lines) - 1} (header: {lines[0].strip()[:80]})")
            if len(lines) > 1:
                print(f"  Sample: {lines[1].strip()[:100]}")
        else:
            print("  FAILED: No CSV output")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
