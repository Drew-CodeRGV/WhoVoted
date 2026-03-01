import sys
sys.path.insert(0, '/opt/whovoted/backend')
import pdfplumber

pdf = '/opt/whovoted/uploads/0343b192-7a18-4ffe-a60a-ae879aed50ca_Voting_History_for_Primary_March_Election_02232026.pdf'

with pdfplumber.open(pdf) as p:
    for i, page in enumerate(p.pages):
        print(f"=== PAGE {i+1} ===")
        # Check for tables
        tables = page.extract_tables()
        if tables:
            print(f"  Tables found: {len(tables)}")
            for ti, t in enumerate(tables):
                print(f"  Table {ti}: {len(t)} rows")
                for row in t[:5]:
                    print(f"    {row}")
        else:
            print("  No tables found")
        
        # Raw text
        text = page.extract_text()
        if text:
            lines = text.split('\n')
            print(f"  Text lines: {len(lines)}")
            for line in lines[:15]:
                print(f"    [{line}]")
        print()
        if i >= 1:
            break
