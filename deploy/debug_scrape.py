import requests, re
r = requests.get('https://www.mcallenisd.org/staff', timeout=15)
html = r.text
print("Length:", len(html))
# Check for Send Message pattern
sm = re.findall(r'Send Message', html, re.IGNORECASE)
print(f"'Send Message' found: {len(sm)} times")
# Check for CLARISSA
if 'CLARISSA' in html:
    idx = html.index('CLARISSA')
    print(f"CLARISSA at index {idx}")
    print("Context:", repr(html[idx-100:idx+200]))
else:
    print("CLARISSA not found")
    # Show first 2000 chars
    print(html[:2000])
