#!/usr/bin/env python3
"""
Import official Hidalgo County canvass results (precinct-by-precinct candidate data)
for the March 3, 2026 primary — HD-41 State Representative race.

Sources:
  Democrat: https://www.hidalgocounty.us/DocumentCenter/View/72302/Democrat-Precinct-Results
  Republican: https://www.hidalgocounty.us/DocumentCenter/View/72303/Republican-Precinct-Results

These are PDFs with precinct-level vote totals for each candidate.
We extract the State Representative District 41 race from each.
"""
import urllib.request, os, sys, json, re, sqlite3
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/data'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_primary_candidates.json'

DEM_PDF_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72302/Democrat-Precinct-Results'
REP_PDF_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72303/Republican-Precinct-Results'

DEM_PDF_PATH = os.path.join(DATA_DIR, 'hidalgo_dem_precinct_results_2026.pdf')
REP_PDF_PATH = os.path.join(DATA_DIR, 'hidalgo_rep_precinct_results_2026.pdf')


def download_pdfs():
    """Download the canvass PDFs."""
    for url, path, label in [(DEM_PDF_URL, DEM_PDF_PATH, 'Democrat'), (REP_PDF_URL, REP_PDF_PATH, 'Republican')]:
        if os.path.exists(path):
            print(f"  {label} PDF already downloaded ({os.path.getsize(path)/1024:.0f} KB)")
            continue
        print(f"  Downloading {label} PDF...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=60)
        with open(path, 'wb') as f:
            f.write(resp.read())
        print(f"  ✓ Saved {label} PDF ({os.path.getsize(path)/1024:.0f} KB)")


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using available tools."""
    # Try pdftotext (poppler-utils)
    import subprocess
    try:
        result = subprocess.run(['pdftotext', '-layout', pdf_path, '-'], capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try PyPDF2 / pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'
        return text
    except ImportError:
        pass

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'
        return text
    except ImportError:
        pass

    print(f"  ERROR: No PDF reader available. Install: apt install poppler-utils OR pip install pypdf")
    return None


def parse_hd41_results(text, party):
    """
    Parse the precinct-by-precinct results for State Representative District 41.
    
    The PDF format varies but typically looks like:
    
    STATE REPRESENTATIVE DISTRICT 41
    Precinct    Candidate1    Candidate2    Candidate3    Total
    0001        123           456           789           1368
    ...
    
    Returns: {precinct: {candidate_name: votes, ...}, ...}
    """
    results = {}
    
    # Find the HD-41 section
    # Look for "STATE REPRESENTATIVE" and "41" or "DISTRICT 41"
    lines = text.split('\n')
    
    in_hd41_section = False
    candidates = []
    
    for i, line in enumerate(lines):
        line_upper = line.upper().strip()
        
        # Detect start of HD-41 section
        if ('STATE REPRESENTATIVE' in line_upper and '41' in line_upper) or \
           ('REPRESENTATIVE.*41' in line_upper) or \
           ('REP.*DIST.*41' in line_upper):
            in_hd41_section = True
            print(f"  Found HD-41 section at line {i}: {line.strip()[:80]}")
            continue
        
        # Also try regex
        if re.search(r'STATE\s+REP.*(?:DIST|DISTRICT)\s*\.?\s*41', line_upper):
            in_hd41_section = True
            print(f"  Found HD-41 section (regex) at line {i}: {line.strip()[:80]}")
            continue
        
        if not in_hd41_section:
            continue
        
        # Detect end of section (next race starts)
        if in_hd41_section and line.strip() and (
            ('STATE REPRESENTATIVE' in line_upper and '41' not in line_upper) or
            ('DISTRICT' in line_upper and '41' not in line_upper and 'STATE' in line_upper) or
            ('COUNTY' in line_upper and 'JUDGE' in line_upper) or
            ('JUSTICE' in line_upper and 'PEACE' in line_upper) or
            ('CONSTABLE' in line_upper) or
            ('COMMISSIONER' in line_upper and 'PRECINCT' not in line_upper)
        ):
            print(f"  End of HD-41 section at line {i}: {line.strip()[:60]}")
            break
        
        # Parse candidate header line (contains candidate names)
        if not candidates and line.strip():
            # Look for a line with multiple words that could be candidate names
            # Usually: "Precinct  Julio Salinas  Victor Haddad  Eric Holguin  Total"
            # Or the candidates might be on separate header lines
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 3:
                # Filter out common non-candidate words
                potential = [p for p in parts if p and p.lower() not in 
                            ('precinct', 'pct', 'total', 'votes', 'race total', 'registered', 'turnout')]
                if len(potential) >= 2 and not any(c.isdigit() for c in potential[0]):
                    candidates = potential
                    print(f"  Candidates: {candidates}")
                    continue
        
        # Parse data rows (precinct + vote counts)
        if candidates and line.strip():
            # Extract numbers from the line
            numbers = re.findall(r'\d+', line)
            if len(numbers) >= len(candidates) + 1:  # precinct + votes for each candidate + total
                precinct = numbers[0]
                votes = [int(n) for n in numbers[1:len(candidates)+1]]
                if len(votes) == len(candidates):
                    results[precinct] = dict(zip(candidates, votes))
            elif len(numbers) >= 2:
                # Try parsing with the first field as precinct
                parts = re.split(r'\s{2,}', line.strip())
                if parts and re.match(r'^\d+', parts[0]):
                    precinct = re.match(r'(\d+)', parts[0]).group(1)
                    vote_numbers = [int(n) for n in numbers[1:] if int(n) < 10000]
                    if len(vote_numbers) >= len(candidates):
                        results[precinct] = dict(zip(candidates, vote_numbers[:len(candidates)]))
    
    return results, candidates


def main():
    print("Importing HD-41 official canvass results...\n")
    
    # Download PDFs
    print("Step 1: Download PDFs")
    download_pdfs()
    
    # Extract text
    print("\nStep 2: Extract text from PDFs")
    dem_text = extract_text_from_pdf(DEM_PDF_PATH)
    rep_text = extract_text_from_pdf(REP_PDF_PATH)
    
    if not dem_text:
        print("ERROR: Could not extract Democrat PDF text")
        # Save raw text for debugging
        return
    if not rep_text:
        print("ERROR: Could not extract Republican PDF text")
        return
    
    # Save extracted text for debugging
    with open(os.path.join(DATA_DIR, 'hidalgo_dem_results_text.txt'), 'w') as f:
        f.write(dem_text)
    with open(os.path.join(DATA_DIR, 'hidalgo_rep_results_text.txt'), 'w') as f:
        f.write(rep_text)
    print(f"  Dem text: {len(dem_text)} chars, Rep text: {len(rep_text)} chars")
    print(f"  Saved raw text to data/ for debugging")
    
    # Parse HD-41 results
    print("\nStep 3: Parse HD-41 State Representative race")
    dem_results, dem_candidates = parse_hd41_results(dem_text, 'Democratic')
    rep_results, rep_candidates = parse_hd41_results(rep_text, 'Republican')
    
    print(f"\n  Democrat results: {len(dem_results)} precincts, candidates: {dem_candidates}")
    print(f"  Republican results: {len(rep_results)} precincts, candidates: {rep_candidates}")
    
    if dem_results:
        # Show first few
        for pct in list(dem_results.keys())[:5]:
            print(f"    Pct {pct}: {dem_results[pct]}")
    
    if rep_results:
        for pct in list(rep_results.keys())[:5]:
            print(f"    Pct {pct}: {rep_results[pct]}")
    
    # If we got results, save to DB and rebuild cache
    if dem_results or rep_results:
        print("\nStep 4: Save to database")
        save_to_db(dem_results, dem_candidates, rep_results, rep_candidates)
        print("\nStep 5: Rebuild candidate cache")
        build_candidate_cache(dem_results, dem_candidates, rep_results, rep_candidates)
    else:
        print("\n  No results parsed. Check the raw text files in data/ to debug the PDF format.")
        print("  The PDF structure may need manual inspection.")
        # Print some context around where we'd expect to find HD-41
        for label, text in [('DEM', dem_text), ('REP', rep_text)]:
            idx = text.upper().find('REPRESENTATIVE')
            if idx >= 0:
                print(f"\n  {label} — text around 'REPRESENTATIVE':")
                print(f"  {text[max(0,idx-50):idx+200]}")


def save_to_db(dem_results, dem_candidates, rep_results, rep_candidates):
    """Save official canvass results to the database."""
    conn = sqlite3.connect(DB_PATH)
    
    # Clear old data
    conn.execute("DELETE FROM hd41_candidate_results WHERE election_date='2026-03-03'")
    
    inserted = 0
    for pct, votes in dem_results.items():
        for candidate, count in votes.items():
            conn.execute("""
                INSERT INTO hd41_candidate_results (election_date, party, candidate, precinct, votes)
                VALUES ('2026-03-03', 'Democratic', ?, ?, ?)
            """, (candidate, pct, count))
            inserted += 1
    
    for pct, votes in rep_results.items():
        for candidate, count in votes.items():
            conn.execute("""
                INSERT INTO hd41_candidate_results (election_date, party, candidate, precinct, votes)
                VALUES ('2026-03-03', 'Republican', ?, ?, ?)
            """, (candidate, pct, count))
            inserted += 1
    
    conn.commit()
    conn.close()
    print(f"  ✓ Inserted {inserted} rows (official canvass data)")


def build_candidate_cache(dem_results, dem_candidates, rep_results, rep_candidates):
    """Build the frontend cache from official canvass data."""
    conn = sqlite3.connect(DB_PATH)
    
    # Get precinct centroids
    centroids = {}
    for pct, lat, lng, voters in conn.execute("""
        SELECT precinct, AVG(lat), AVG(lng), COUNT(*)
        FROM voters WHERE state_house_district='HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall():
        # Normalize precinct for matching
        norm = pct.lstrip('0') or '0'
        if '.' in pct:
            norm = pct.split('.')[0].lstrip('0') or '0'
        centroids[norm] = {'lat': round(lat, 4), 'lng': round(lng, 4), 'registered': voters}
    conn.close()
    
    # Build candidate analysis from REAL data
    all_candidates = {}
    
    for party, results, cand_list in [('Democratic', dem_results, dem_candidates), ('Republican', rep_results, rep_candidates)]:
        party_total = {}
        for pct, votes in results.items():
            for c, v in votes.items():
                party_total[c] = party_total.get(c, 0) + v
        
        for candidate in cand_list:
            total = party_total.get(candidate, 0)
            party_grand_total = sum(party_total.values()) // len(cand_list) if cand_list else 1  # avoid double-counting
            # Actually sum all votes for this party across all precincts
            party_votes_total = sum(sum(v.values()) for v in results.values()) // len(cand_list) if cand_list else 1
            
            precinct_data = []
            for pct, votes in results.items():
                my_votes = votes.get(candidate, 0)
                pct_total = sum(votes.values())
                share = round(my_votes / pct_total * 100, 1) if pct_total > 0 else 0
                
                beaten_by = [{'candidate': c, 'votes': v, 'share': round(v/pct_total*100, 1)}
                             for c, v in votes.items() if c != candidate and v > my_votes]
                
                centroid = centroids.get(pct, centroids.get(pct.lstrip('0'), {}))
                
                precinct_data.append({
                    'precinct': pct,
                    'votes': my_votes,
                    'pct_total': pct_total,
                    'share': share,
                    'lat': centroid.get('lat'),
                    'lng': centroid.get('lng'),
                    'registered': centroid.get('registered', 0),
                    'beaten_by': beaten_by,
                })
            
            precinct_data.sort(key=lambda x: x['share'], reverse=True)
            
            all_candidates[candidate] = {
                'party': party,
                'total_votes': total,
                'district_share': round(total / (sum(party_total.values()) or 1) * 100, 1),
                'precincts': precinct_data,
                'strong_precincts': len([p for p in precinct_data if p['share'] >= 50]),
                'weak_precincts': len([p for p in precinct_data if p['share'] < 25]),
                'top_5': precinct_data[:5],
                'bottom_5': precinct_data[-5:],
            }
    
    output = {
        'election_date': '2026-03-03',
        'district': 'HD-41',
        'source': 'Hidalgo County Official Canvass (precinct-by-precinct)',
        'source_urls': {
            'Democratic': DEM_PDF_URL,
            'Republican': REP_PDF_URL,
        },
        'dem_candidates': dem_candidates,
        'rep_candidates': rep_candidates,
        'candidates': all_candidates,
    }
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    
    print(f"  ✓ Cache: {Path(CACHE_PATH).stat().st_size/1024:.0f} KB")
    for c, d in all_candidates.items():
        print(f"    {c} ({d['party']}): {d['total_votes']} votes ({d['district_share']}%)")


if __name__ == '__main__':
    main()
