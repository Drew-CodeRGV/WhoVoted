import sys
sys.path.insert(0, '/opt/whovoted/backend')

from pdf_extractor import extract_pdf_to_csv
import glob, os

# Try the first Brooks PDF
pdfs = sorted(glob.glob('/opt/whovoted/uploads/*Voting_History*'))
if not pdfs:
    print("No PDFs found")
    sys.exit(1)

pdf = pdfs[0]
print(f"Testing: {os.path.basename(pdf)}")
print(f"Size: {os.path.getsize(pdf)} bytes")

try:
    csv_path = extract_pdf_to_csv(pdf)
    print(f"Extracted to: {csv_path}")
    
    import pandas as pd
    df = pd.read_csv(csv_path)
    print(f"\n{len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")
    if len(df) > 0:
        print(f"\nFirst 5 rows:")
        print(df.head(5).to_string())
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
