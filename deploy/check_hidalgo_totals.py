#!/usr/bin/env python3
"""Check Hidalgo County totals vs official numbers."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def check_totals():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Official numbers from PDF (bottom right corner)
    official_dem = 19064
    official_rep = 13137
    official_total = 32283
    
    print("=" * 70)
    print("HIDALGO COUNTY 2026 PRIMARY - OFFICIAL VS DATABASE")
    print("=" * 70)
    
    # Check our database totals for Hidalgo County, 2026-03-03
    result = conn.execute("""
        SELECT 
            COUNT(*) as total_records,
            SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
            SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
            SUM(CASE WHEN ve.party_voted != '' AND ve.party_voted IS NOT NULL THEN 1 ELSE 0 END) as total_with_party
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
    """).fetchone()
    
    db_dem = result['dem']
    db_rep = result['rep']
    db_total = result['total_with_party']
    db_records = result['total_records']
    
    print(f"\nOFFICIAL NUMBERS (from PDF):")
    print(f"  Democratic:  {official_dem:>6,}")
    print(f"  Republican:  {official_rep:>6,}")
    print(f"  Total:       {official_total:>6,}")
    
    print(f"\nDATABASE NUMBERS:")
    print(f"  Democratic:  {db_dem:>6,}")
    print(f"  Republican:  {db_rep:>6,}")
    print(f"  Total:       {db_total:>6,}")
    print(f"  (Total records: {db_records:,})")
    
    print(f"\nDIFFERENCE:")
    print(f"  Democratic:  {db_dem - official_dem:>+6,} ({(db_dem/official_dem-1)*100:+.1f}%)")
    print(f"  Republican:  {db_rep - official_rep:>+6,} ({(db_rep/official_rep-1)*100:+.1f}%)")
    print(f"  Total:       {db_total - official_total:>+6,} ({(db_total/official_total-1)*100:+.1f}%)")
    
    # Check for records without party
    no_party = conn.execute("""
        SELECT COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
          AND (ve.party_voted = '' OR ve.party_voted IS NULL)
    """).fetchone()['cnt']
    
    if no_party > 0:
        print(f"\n⚠️  WARNING: {no_party:,} records have no party affiliation")
    
    # Check for duplicate VUIDs
    dupes = conn.execute("""
        SELECT COUNT(*) as cnt
        FROM (
            SELECT ve.vuid, COUNT(*) as vote_count
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE v.county = 'Hidalgo'
              AND ve.election_date = '2026-03-03'
            GROUP BY ve.vuid
            HAVING COUNT(*) > 1
        )
    """).fetchone()['cnt']
    
    if dupes > 0:
        print(f"⚠️  WARNING: {dupes:,} VUIDs have multiple votes for same election")
    
    # Check election dates in database
    print(f"\nELECTION DATES IN DATABASE:")
    dates = conn.execute("""
        SELECT DISTINCT ve.election_date, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
        GROUP BY ve.election_date
        ORDER BY ve.election_date DESC
        LIMIT 5
    """).fetchall()
    
    for row in dates:
        print(f"  {row['election_date']}: {row['cnt']:,} votes")
    
    # Check if we're counting early voting only or all voting
    print(f"\nVOTING METHOD BREAKDOWN (2026-03-03):")
    methods = conn.execute("""
        SELECT 
            ve.voting_method,
            COUNT(*) as cnt,
            SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
            SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
        GROUP BY ve.voting_method
    """).fetchall()
    
    for row in methods:
        method = row['voting_method'] or 'NULL'
        print(f"  {method:20s}: {row['cnt']:>6,} total ({row['dem']:>6,} D, {row['rep']:>6,} R)")
    
    conn.close()
    
    print("\n" + "=" * 70)
    
    # Determine likely cause
    if db_total > official_total:
        print("\n🔍 LIKELY CAUSE: Database includes Election Day votes, not just Early Voting")
        print("   The official PDF shows 'EARLY VOTING' totals only.")
        print("   Our database may be counting all votes (early + election day).")
    elif db_total < official_total:
        print("\n🔍 LIKELY CAUSE: Database is missing some records")
        print("   Check if the latest scrape completed successfully.")
    else:
        print("\n✅ Totals match!")

if __name__ == '__main__':
    check_totals()
