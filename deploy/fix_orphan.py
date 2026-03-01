#!/usr/bin/env python3
import sqlite3
c = sqlite3.connect("/opt/whovoted/data/whovoted.db")
c.execute("INSERT OR IGNORE INTO voters (vuid, county, current_party, geocoded, updated_at) VALUES ('2212573782', 'Hidalgo', 'Republican', 0, datetime('now'))")
c.commit()
print("Fixed orphan VUID")
