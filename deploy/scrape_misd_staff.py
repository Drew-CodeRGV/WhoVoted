#!/usr/bin/env python3
"""Scrape McAllen ISD staff directory and match against bond voters."""
import requests, re, sqlite3, csv, time

BASE = 'https://www.mcallenisd.org/staff'
DB = '/opt/whovoted/data/whovoted.db'
ELECTION = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')

def scrape_all_staff():
    """Scrape all pages of the MISD staff directory."""
    all_staff = []
    seen = set()
    
    for page in range(1, 100):  # safety limit
        url = f'{BASE}?page_no={page}'
        print(f"  Fetching page {page}...", end=' ')
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"Error: {e}")
            break
        
        # Extract staff names - pattern: all caps name followed by title
        # The page structure has: NAME\nTITLE\nDEPARTMENT\nPHONE
        # Names are in all caps, appear before job titles
        # Look for the pattern in the raw text between staff entries
        
        # Try to find names using the "Send Message to NAME" pattern
        names = re.findall(r'Send Message\s*to\s+([A-Z][A-Z\s\'.,-]+?)(?:\s*<|\s*$)', html, re.MULTILINE)
        
        if not names:
            # Fallback: look for the staff card pattern
            # Names appear as all-caps text blocks
            names = re.findall(r'<div[^>]*class="[^"]*staff[^"]*name[^"]*"[^>]*>([^<]+)</div>', html, re.IGNORECASE)
        
        if not names:
            # Another pattern: names in the truncated format
            # FIRST LAST followed by job title in caps
            blocks = re.findall(r'>([A-Z][A-Z \'.\-]{3,40})<', html)
            # Filter to likely names (not titles/departments)
            job_words = {'SUBSTITUTE', 'TEACHER', 'COORD', 'DIR', 'CLERK', 'BUS', 'DRIVER',
                        'CARPENTER', 'SPEC', 'TECH', 'DISTRICT', 'TRANSPORTATION', 'PAYROLL',
                        'INSTRUCTIONAL', 'LEADERSHIP', 'TECHNOLOGY', 'FINE', 'ARTS', 'OPERATIONS',
                        'STUDENT', 'FACILITIES', 'MAINT', 'OPS', 'RESOURCES', 'PURCHASING',
                        'SOCIAL', 'STUDIES', 'DEGREED', 'DEG', 'CERT', 'NON', 'CUSTODIAN',
                        'PRINCIPAL', 'ASST', 'SECRETARY', 'NURSE', 'COUNSELOR', 'LIBRARIAN',
                        'CAFETERIA', 'MANAGER', 'AIDE', 'PARA', 'PROFESSIONAL', 'COACH',
                        'ATHLETIC', 'MAINTENANCE', 'GROUNDSKEEPER', 'ELECTRICIAN', 'PLUMBER',
                        'HVAC', 'POLICE', 'OFFICER', 'SECURITY', 'GUARD', 'FOOD', 'SERVICE',
                        'SPECIAL', 'EDUCATION', 'BILINGUAL', 'ESL', 'MATH', 'SCIENCE',
                        'ENGLISH', 'READING', 'HISTORY', 'MUSIC', 'ART', 'PE', 'PHYSICAL',
                        'HEALTH', 'CAREER', 'CTE', 'ASSESSMENT', 'CURRICULUM', 'HUMAN',
                        'FINANCE', 'BUDGET', 'ACCOUNTING', 'WAREHOUSE', 'DELIVERY',
                        'RECEPTIONIST', 'REGISTRAR', 'ATTENDANCE', 'DATA', 'ENTRY',
                        'MCALLEN', 'INDEPENDENT', 'SCHOOL', 'SEARCH', 'SITE', 'MENU',
                        'SIGN', 'TRANSLATE', 'SCHOOLS', 'HOME', 'RETURN', 'FILTER',
                        'DEPARTMENTS', 'SELECT', 'USE', 'THE', 'FIELD', 'ABOVE', 'NAME',
                        'STAFF', 'LINKS', 'EMPLOYMENT', 'CONTACT', 'ONLINE', 'STORE',
                        'REGISTER', 'HERE', 'ENROLL', 'WITH', 'EXCELLENCE', 'EDUCATION'}
            names = []
            for b in blocks:
                words = b.strip().split()
                if len(words) >= 2 and not any(w in job_words for w in words):
                    names.append(b.strip())
        
        if not names:
            print(f"No names found, stopping.")
            break
        
        count = 0
        for name in names:
            name = name.strip()
            if name and name not in seen and len(name) > 3:
                seen.add(name)
                all_staff.append(name)
                count += 1
        
        print(f"{count} new names (total: {len(all_staff)})")
        
        # Check if this is the last page
        if f'page_no={page + 1}' not in html:
            print("  Last page reached.")
            break
        
        time.sleep(0.3)  # be polite
    
    return all_staff

def match_voters(staff_names):
    """Match staff names against voter database."""
    conn = sqlite3.connect(DB)
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    
    # Get all voters who voted in the bond
    voters = conn.execute(f"""
        SELECT UPPER(v.firstname || ' ' || v.lastname) as full_name,
               v.firstname, v.lastname, v.vuid
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph})
    """, (ELECTION,) + MCALLEN_ZIPS).fetchall()
    
    # Also get all registered voters for the "registered but didn't vote" count
    all_registered = conn.execute(f"""
        SELECT UPPER(v.firstname || ' ' || v.lastname) as full_name,
               v.firstname, v.lastname, v.vuid
        FROM voters v
        WHERE v.zip IN ({ph})
    """, MCALLEN_ZIPS).fetchall()
    conn.close()
    
    # Build lookup sets
    voter_names = set()
    for full, first, last, vuid in voters:
        if first and last:
            voter_names.add(f"{first.upper().strip()} {last.upper().strip()}")
    
    registered_names = set()
    for full, first, last, vuid in all_registered:
        if first and last:
            registered_names.add(f"{first.upper().strip()} {last.upper().strip()}")
    
    # Match staff against voters
    matched_voted = []
    matched_registered = []
    unmatched = []
    
    # Deduplicate staff names
    unique_staff = list(dict.fromkeys(staff_names))  # preserves order, removes dupes
    
    for name in unique_staff:
        name_upper = name.upper().strip()
        # Try exact match
        if name_upper in voter_names:
            matched_voted.append(name)
        elif name_upper in registered_names:
            matched_registered.append(name)
        else:
            # Try last,first format or partial match
            parts = name_upper.split()
            if len(parts) >= 2:
                # Try first + last
                first = parts[0]
                last = parts[-1]
                alt = f"{first} {last}"
                if alt in voter_names:
                    matched_voted.append(name)
                elif alt in registered_names:
                    matched_registered.append(name)
                else:
                    unmatched.append(name)
            else:
                unmatched.append(name)
    
    return unique_staff, matched_voted, matched_registered, unmatched

def main():
    print("=== Scraping McAllen ISD Staff Directory ===")
    staff = scrape_all_staff()
    print(f"\nTotal staff scraped: {len(staff)}")
    
    # Save to CSV
    csv_path = '/opt/whovoted/data/misd_staff.csv'
    with open(csv_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['name'])
        for name in staff:
            w.writerow([name])
    print(f"Saved to {csv_path}")
    
    print("\n=== Matching Against Voter Database ===")
    unique, voted, registered, unmatched = match_voters(staff)
    
    print(f"\nUnique staff names: {len(unique)}")
    print(f"Matched to bond voters: {len(voted)} ({len(voted)/len(unique)*100:.1f}%)")
    print(f"Registered but didn't vote: {len(registered)} ({len(registered)/len(unique)*100:.1f}%)")
    print(f"Not found in voter rolls: {len(unmatched)} ({len(unmatched)/len(unique)*100:.1f}%)")
    
    print(f"\nOf staff found in voter rolls: {len(voted)}/{len(voted)+len(registered)} voted ({len(voted)/(len(voted)+len(registered))*100:.1f}%)" if (len(voted)+len(registered)) > 0 else "")
    
    print("\n--- Sample voted staff ---")
    for name in voted[:20]:
        print(f"  {name}")
    
    print("\n--- Sample registered but didn't vote ---")
    for name in registered[:20]:
        print(f"  {name}")

if __name__ == '__main__':
    main()
