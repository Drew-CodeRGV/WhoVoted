#!/usr/bin/env python3
"""Fix duplicate VUID counting by removing duplicate voter_elections records."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def fix_duplicates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print("="*70)
    print("FIXING DUPLICATE VUID COUNTING")
    print("="*70)
    
    # Find duplicates
    dupes = conn.execute("""
        SELECT ve.vuid, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
        GROUP BY ve.vuid
        HAVING COUNT(*) > 1
    """).fetchall()
    
    print(f"\nFound {len(dupes)} duplicate VUIDs")
    
    if not dupes:
        print("No duplicates to fix!")
        conn.close()
        return
    
    # For each duplicate, keep only the first record (by rowid)
    for row in dupes:
        vuid = row['vuid']
        
        # Get all records for this VUID
        records = conn.execute("""
            SELECT rowid, voting_method, party_voted
            FROM voter_elections
            WHERE vuid = ? AND election_date = '2026-03-03'
            ORDER BY rowid
        """, [vuid]).fetchall()
        
        print(f"\nVUID {vuid}: {len(records)} records")
        for r in records:
            print(f"  rowid={r['rowid']}: {r['party_voted']} via {r['voting_method']}")
        
        # Keep first record, delete the rest
        keep_rowid = records[0]['rowid']
        delete_rowids = [r['rowid'] for r in records[1:]]
        
        print(f"  → Keeping rowid={keep_rowid}, deleting {len(delete_rowids)} duplicate(s)")
        
        for rowid in delete_rowids:
            conn.execute("DELETE FROM voter_elections WHERE rowid = ?", [rowid])
    
    conn.commit()
    
    # Verify fix
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    
    result = conn.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT ve.vuid) as unique_vuids,
            SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
            SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
    """).fetchone()
    
    print(f"\nAfter fix:")
    print(f"  Total records: {result['total']:,}")
    print(f"  Unique VUIDs: {result['unique_vuids']:,}")
    print(f"  Democratic: {result['dem']:,}")
    print(f"  Republican: {result['rep']:,}")
    print(f"  Total: {result['dem'] + result['rep']:,}")
    
    print(f"\nOfficial numbers:")
    print(f"  Democratic: 49,664")
    print(f"  Republican: 13,217")
    print(f"  Total: 62,881")
    
    print(f"\nDifference:")
    print(f"  Democratic: {result['dem'] - 49664:+,}")
    print(f"  Republican: {result['rep'] - 13217:+,}")
    print(f"  Total: {(result['dem'] + result['rep']) - 62881:+,}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ Duplicates removed!")
    print("="*70)

if __name__ == '__main__':
    fix_duplicates()
