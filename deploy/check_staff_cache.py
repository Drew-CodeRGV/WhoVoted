import json
d = json.load(open('/opt/whovoted/public/cache/misdbond2026_staff.json'))
print("Keys:", list(d.keys()))
print("Has roles:", 'roles' in d, "count:", len(d.get('roles', [])))
for r in d.get('roles', []):
    print(f"  {r['icon']} {r['role']}: {r['voted']}/{r['matched']} of {r['total']} ({r['turnout_pct']}%)")
print(f"Overall: {d['voted']}/{d['matched_to_voters']} ({d['turnout_pct']}%)")
