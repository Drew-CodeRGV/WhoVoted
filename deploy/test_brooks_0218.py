import sys
sys.path.insert(0, '/opt/whovoted/backend')
import pdfplumber

pdf = '/opt/whovoted/uploads/0cca8330-19f4-4cf4-835a-78d31a87e2c0_Voting_History_for_Primary_March_Election_02182026.pdf'

with pdfplumber.open(pdf) as p:
    page = p.pages[0]
    text = page.extract_text()
    lines = text.split('\n')
    for line in lines[:15]:
        print(f"[{line}]")
