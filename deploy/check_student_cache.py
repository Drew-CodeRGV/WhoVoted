import json
d = json.load(open('/opt/whovoted/public/cache/misdbond2026_students.json'))
print("Summary:", json.dumps(d['summary'], indent=2))
# Show a sample tract
if d['tracts']:
    print("Sample tract:", json.dumps(d['tracts'][0]))
