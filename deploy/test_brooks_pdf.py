import sys
sys.path.insert(0, '/opt/whovoted/backend')

from pdf_extractor import extract_data_from_pdf
import glob

# Try the first Brooks PDF
pdfs = sorted(glob.glob('/opt/whovoted/uploads/*Voting_History*'))
if not pdfs:
    print("No PDFs found")
    sys.exit(1)

pdf = pdfs[0]
print(f"Testing: {pdf}")
print(f"Size: {__import__('os').path.getsize(pdf)} bytes")

try:
    df = extract_data_from_pdf(pdf)
    print(f"\nExtracted {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")
    if len(df) > 0:
        print(f"\nFirst 3 rows:")
        print(df.head(3).to_string())
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Also try read_data_file
print("\n\n--- Testing read_data_file ---")
try:
    from processor import read_data_file
    df2 = read_data_file(pdf)
    print(f"read_data_file got {len(df2)} rows, {len(df2.columns)} columns")
    print(f"Columns: {list(df2.columns)}")
    if len(df2) > 0:
        print(f"\nFirst 3 rows:")
        print(df2.head(3).to_string())
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
