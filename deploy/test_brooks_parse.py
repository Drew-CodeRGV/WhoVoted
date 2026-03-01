import sys
sys.path.insert(0, '/opt/whovoted/backend')

from pdf_extractor import extract_pdf_to_csv
import glob, os, csv

# Test all Brooks PDFs
pdfs = sorted(glob.glob('/opt/whovoted/uploads/*Voting_History*'))
print(f"Found {len(pdfs)} Brooks PDFs\n")

for pdf in pdfs:
    fname = os.path.basename(pdf).split('_', 1)[1]  # Remove UUID prefix
    print(f"--- {fname} ---")
    try:
        # Remove old extracted CSV if exists
        old_csv = pdf.replace('.pdf', '_extracted.csv')
        if os.path.exists(old_csv):
            os.unlink(old_csv)
        
        csv_path = extract_pdf_to_csv(pdf)
        with open(csv_path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        print(f"  Rows: {len(rows) - 1} (+ header)")
        if rows:
            print(f"  Header: {rows[0]}")
        if len(rows) > 1:
            print(f"  Row 1: {rows[1]}")
            # Count DEM vs REP
            party_idx = rows[0].index('party') if 'party' in rows[0] else -1
            if party_idx >= 0:
                parties = {}
                for r in rows[1:]:
                    if len(r) > party_idx:
                        p = r[party_idx]
                        parties[p] = parties.get(p, 0) + 1
                print(f"  Parties: {parties}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
