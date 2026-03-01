#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT vuid, firstname, lastname, middlename FROM voters WHERE lastname='LONGORIA' AND firstname='DANIEL' AND middlename LIKE 'A%'").fetchall()
for r in rows:
    print("VUID:", r['vuid'], "Name:", r['firstname'], r['middlename'], r['lastname'])
    elections = conn.execute("SELECT election_date, party_voted FROM voter_elections WHERE vuid=? ORDER BY election_date", (r['vuid'],)).fetchall()
    for e in elections:
        print("  ", e['election_date'], ":", e['party_voted'])
    # Test API
    import urllib.request, json
    try:
        resp = urllib.request.urlopen("http://localhost:5000/api/voter-history/" + r['vuid'])
        data = json.loads(resp.read())
        print("  API:", [(h['year'], h['party']) for h in data.get('history', [])])
    except Exception as ex:
        print("  API error:", ex)
conn.close()
