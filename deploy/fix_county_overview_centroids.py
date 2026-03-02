#!/usr/bin/env python3
"""
Fix county overview cache files to use proper county centroids instead of
averaging voter coordinates (which are mostly missing for non-Hidalgo counties).
"""
import sqlite3
import json
import os
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'

# Texas county centroids (approximate centers)
COUNTY_CENTROIDS = {
    'Anderson': (31.8, -95.65),
    'Andrews': (32.3, -102.6),
    'Angelina': (31.3, -94.6),
    'Aransas': (28.1, -97.05),
    'Archer': (33.6, -98.7),
    'Armstrong': (34.95, -101.35),
    'Atascosa': (28.9, -98.5),
    'Austin': (29.9, -96.3),
    'Bailey': (34.05, -102.85),
    'Bandera': (29.75, -99.2),
    'Bastrop': (30.1, -97.3),
    'Baylor': (33.6, -99.2),
    'Bee': (28.4, -97.75),
    'Bell': (31.05, -97.5),
    'Bexar': (29.45, -98.5),
    'Blanco': (30.25, -98.4),
    'Borden': (32.85, -101.45),
    'Bosque': (31.9, -97.65),
    'Bowie': (33.45, -94.4),
    'Brazoria': (29.2, -95.45),
    'Brazos': (30.65, -96.3),
    'Brewster': (29.8, -103.25),
    'Briscoe': (34.55, -101.15),
    'Brooks': (27.0, -98.2),
    'Brown': (31.8, -99.0),
    'Burleson': (30.5, -96.6),
    'Burnet': (30.75, -98.2),
    'Caldwell': (29.85, -97.6),
    'Calhoun': (28.4, -96.6),
    'Callahan': (32.3, -99.35),
    'Cameron': (26.15, -97.45),
    'Camp': (32.95, -94.95),
    'Carson': (35.4, -101.35),
    'Cass': (33.1, -94.35),
    'Castro': (34.55, -102.25),
    'Chambers': (29.7, -94.7),
    'Cherokee': (31.85, -95.2),
    'Childress': (34.45, -100.2),
    'Clay': (33.8, -98.2),
    'Cochran': (33.6, -102.8),
    'Coke': (31.9, -100.5),
    'Coleman': (31.8, -99.45),
    'Collin': (33.2, -96.6),
    'Collingsworth': (34.95, -100.25),
    'Colorado': (29.6, -96.5),
    'Comal': (29.8, -98.3),
    'Comanche': (31.9, -98.6),
    'Concho': (31.4, -99.85),
    'Cooke': (33.65, -97.2),
    'Coryell': (31.4, -97.8),
    'Cottle': (34.05, -100.3),
    'Crane': (31.4, -102.35),
    'Crockett': (30.75, -101.4),
    'Crosby': (33.6, -101.3),
    'Culberson': (31.45, -104.5),
    'Dallam': (36.3, -102.5),
    'Dallas': (32.75, -96.8),
    'Dawson': (32.75, -101.95),
    'Deaf Smith': (34.95, -102.6),
    'Delta': (33.4, -95.65),
    'Denton': (33.2, -97.1),
    'DeWitt': (29.05, -97.4),
    'Dewitt': (29.05, -97.4),  # Alternate capitalization
    'Dickens': (33.65, -100.8),
    'Dimmit': (28.45, -99.75),
    'Donley': (35.0, -100.8),
    'Duval': (27.7, -98.5),
    'Eastland': (32.4, -98.8),
    'Ector': (31.85, -102.5),
    'Edwards': (30.0, -100.3),
    'Ellis': (32.35, -96.8),
    'El Paso': (31.8, -106.4),
    'Erath': (32.2, -98.2),
    'Falls': (31.2, -96.9),
    'Fannin': (33.6, -96.1),
    'Fayette': (29.9, -96.9),
    'Fisher': (32.75, -100.4),
    'Floyd': (34.0, -101.3),
    'Foard': (33.95, -99.75),
    'Fort Bend': (29.5, -95.75),
    'Franklin': (33.2, -95.2),
    'Freestone': (31.7, -96.15),
    'Frio': (28.85, -99.1),
    'Gaines': (32.75, -102.65),
    'Galveston': (29.4, -94.9),
    'Garza': (33.2, -101.3),
    'Gillespie': (30.3, -99.0),
    'Glasscock': (31.85, -101.5),
    'Goliad': (28.65, -97.4),
    'Gonzales': (29.5, -97.45),
    'Gray': (35.4, -100.8),
    'Grayson': (33.6, -96.65),
    'Gregg': (32.5, -94.8),
    'Grimes': (30.55, -95.95),
    'Guadalupe': (29.6, -98.0),
    'Hale': (34.05, -101.8),
    'Hall': (34.55, -100.7),
    'Hamilton': (31.7, -98.1),
    'Hansford': (36.3, -101.35),
    'Hardeman': (34.3, -99.75),
    'Hardin': (30.3, -94.4),
    'Harris': (29.85, -95.4),
    'Harrison': (32.55, -94.35),
    'Hartley': (35.9, -102.5),
    'Haskell': (33.2, -99.75),
    'Hays': (30.0, -98.0),
    'Hemphill': (35.85, -100.25),
    'Henderson': (32.2, -95.85),
    'Hidalgo': (26.3, -98.2),
    'Hill': (32.0, -97.1),
    'Hockley': (33.6, -102.35),
    'Hood': (32.45, -97.8),
    'Hopkins': (33.15, -95.55),
    'Houston': (31.35, -95.45),
    'Howard': (32.3, -101.45),
    'Hudspeth': (31.45, -105.4),
    'Hunt': (33.1, -96.1),
    'Hutchinson': (35.85, -101.35),
    'Irion': (31.25, -100.95),
    'Jack': (33.2, -98.2),
    'Jackson': (28.95, -96.55),
    'Jasper': (30.7, -94.0),
    'Jeff Davis': (30.65, -104.2),
    'Jefferson': (29.9, -94.1),
    'Jim Hogg': (27.0, -98.7),
    'Jim Wells': (27.7, -98.1),
    'Johnson': (32.4, -97.4),
    'Jones': (32.75, -99.85),
    'Karnes': (28.9, -97.9),
    'Kaufman': (32.6, -96.3),
    'Kendall': (29.95, -98.7),
    'Kenedy': (26.9, -97.65),
    'Kent': (33.2, -100.8),
    'Kerr': (30.05, -99.35),
    'Kimble': (30.5, -99.75),
    'King': (33.6, -100.25),
    'Kinney': (29.35, -100.4),
    'Kleberg': (27.5, -97.7),
    'Knox': (33.6, -99.75),
    'Lamar': (33.65, -95.55),
    'Lamb': (34.05, -102.35),
    'Lampasas': (31.2, -98.2),
    'La Salle': (28.35, -99.1),
    'Lasalle': (28.35, -99.1),  # Alternate capitalization
    'Lavaca': (29.4, -96.9),
    'Lee': (30.3, -96.95),
    'Leon': (31.3, -96.0),
    'Liberty': (30.1, -94.8),
    'Limestone': (31.55, -96.6),
    'Lipscomb': (36.3, -100.25),
    'Live Oak': (28.35, -98.1),
    'Llano': (30.7, -98.7),
    'Loving': (31.85, -103.6),
    'Lubbock': (33.6, -101.85),
    'Lynn': (33.2, -101.8),
    'McCulloch': (31.2, -99.35),
    'Mcculloch': (31.2, -99.35),  # Alternate capitalization
    'McLennan': (31.55, -97.2),
    'Mclennan': (31.55, -97.2),  # Alternate capitalization
    'McMullen': (28.35, -98.55),
    'Mcmullen': (28.35, -98.55),  # Alternate capitalization
    'Madison': (30.95, -95.9),
    'Marion': (32.8, -94.35),
    'Martin': (32.3, -101.95),
    'Mason': (30.75, -99.25),
    'Matagorda': (28.95, -95.95),
    'Maverick': (28.75, -100.4),
    'Medina': (29.35, -99.15),
    'Menard': (30.9, -99.8),
    'Midland': (31.85, -102.0),
    'Milam': (30.8, -96.95),
    'Mills': (31.5, -98.6),
    'Mitchell': (32.3, -100.9),
    'Montague': (33.65, -97.7),
    'Montgomery': (30.3, -95.5),
    'Moore': (35.85, -101.9),
    'Morris': (33.1, -94.75),
    'Motley': (34.05, -100.8),
    'Nacogdoches': (31.6, -94.65),
    'Navarro': (32.0, -96.5),
    'Newton': (30.8, -93.75),
    'Nolan': (32.3, -100.4),
    'Nueces': (27.7, -97.6),
    'Ochiltree': (36.3, -100.8),
    'Oldham': (35.4, -102.6),
    'Orange': (30.1, -93.9),
    'Palo Pinto': (32.75, -98.3),
    'Panola': (32.2, -94.3),
    'Parker': (32.8, -97.8),
    'Parmer': (34.55, -102.8),
    'Pecos': (30.85, -102.6),
    'Polk': (30.75, -94.85),
    'Potter': (35.4, -101.9),
    'Presidio': (29.95, -104.4),
    'Rains': (32.9, -95.8),
    'Randall': (34.95, -101.9),
    'Reagan': (31.35, -101.5),
    'Real': (29.8, -99.8),
    'Red River': (33.6, -95.05),
    'Reeves': (31.3, -103.6),
    'Refugio': (28.3, -97.3),
    'Roberts': (35.85, -100.8),
    'Robertson': (31.0, -96.5),
    'Rockwall': (32.9, -96.4),
    'Runnels': (31.85, -100.0),
    'Rusk': (32.1, -94.75),
    'Sabine': (31.35, -93.85),
    'San Augustine': (31.4, -94.1),
    'San Jacinto': (30.55, -95.2),
    'San Patricio': (27.95, -97.5),
    'San Saba': (31.2, -98.7),
    'Schleicher': (30.85, -100.5),
    'Scurry': (32.75, -100.9),
    'Shackelford': (32.75, -99.35),
    'Shelby': (31.8, -94.15),
    'Sherman': (36.3, -101.9),
    'Smith': (32.4, -95.3),
    'Somervell': (32.2, -97.8),
    'Starr': (26.55, -98.75),
    'Stephens': (32.75, -98.8),
    'Sterling': (31.85, -101.0),
    'Stonewall': (33.2, -100.25),
    'Sutton': (30.5, -100.55),
    'Swisher': (34.55, -101.7),
    'Tarrant': (32.75, -97.3),
    'Taylor': (32.3, -99.9),
    'Terrell': (30.25, -102.1),
    'Terry': (33.2, -102.35),
    'Throckmorton': (33.2, -99.2),
    'Titus': (33.2, -94.95),
    'Tom Green': (31.4, -100.45),
    'Travis': (30.3, -97.7),
    'Trinity': (31.1, -95.1),
    'Tyler': (30.75, -94.4),
    'Upshur': (32.75, -94.95),
    'Upton': (31.35, -102.0),
    'Uvalde': (29.2, -99.8),
    'Val Verde': (29.9, -101.0),
    'Van Zandt': (32.55, -95.85),
    'Victoria': (28.8, -97.0),
    'Walker': (30.75, -95.55),
    'Waller': (30.05, -96.1),
    'Ward': (31.5, -103.1),
    'Washington': (30.2, -96.4),
    'Webb': (27.55, -99.5),
    'Wharton': (29.3, -96.15),
    'Wheeler': (35.4, -100.25),
    'Wichita': (33.95, -98.7),
    'Wilbarger': (34.05, -99.2),
    'Willacy': (26.5, -97.6),
    'Williamson': (30.6, -97.6),
    'Wilson': (29.2, -98.1),
    'Winkler': (31.85, -103.0),
    'Wise': (33.2, -97.65),
    'Wood': (32.8, -95.4),
    'Yoakum': (33.2, -102.8),
    'Young': (33.2, -98.7),
    'Zapata': (26.9, -99.2),
    'Zavala': (28.85, -99.75),
}

def rebuild_county_overview(election_date, voting_method=None):
    """Rebuild county overview with proper centroids."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    where = "WHERE ve.election_date = ? AND ve.party_voted IN ('Democratic', 'Republican')"
    params = [election_date]
    if voting_method:
        where += " AND ve.voting_method = ?"
        params.append(voting_method)
    
    # Get vote counts per county
    rows = conn.execute(f"""
        SELECT v.county,
               COUNT(DISTINCT ve.vuid) as total,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where}
        GROUP BY v.county
        ORDER BY total DESC
    """, params).fetchall()
    
    counties = []
    for r in rows:
        county = r['county']
        if not county or county == 'Unknown':
            continue
        
        # Use proper centroid from lookup table
        if county in COUNTY_CENTROIDS:
            lat, lng = COUNTY_CENTROIDS[county]
        else:
            print(f"  Warning: No centroid for {county}, skipping")
            continue
        
        counties.append({
            'county': county,
            'lat': round(lat, 4),
            'lng': round(lng, 4),
            'total': r['total'],
            'dem': r['dem'],
            'rep': r['rep'],
        })
    
    conn.close()
    
    # Save to cache
    method_str = voting_method or 'all'
    cache_file = os.path.join(CACHE_DIR, f'county_overview_{election_date}_{method_str}.json')
    with open(cache_file, 'w') as f:
        json.dump({'success': True, 'counties': counties}, f, separators=(',', ':'))
    
    print(f"  ✓ {cache_file}: {len(counties)} counties, {sum(c['total'] for c in counties):,} total voters")
    return len(counties)

def main():
    print("Rebuilding county overview cache files with proper centroids...\n")
    
    # Get all unique election_date + voting_method combinations
    conn = sqlite3.connect(DB_PATH)
    datasets = conn.execute("""
        SELECT DISTINCT election_date, voting_method
        FROM voter_elections
        WHERE party_voted IN ('Democratic', 'Republican')
        ORDER BY election_date DESC, voting_method
    """).fetchall()
    conn.close()
    
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    total_files = 0
    for ed, vm in datasets:
        print(f"{ed} / {vm or 'all'}:")
        rebuild_county_overview(ed, vm)
        total_files += 1
    
    print(f"\n✅ Rebuilt {total_files} county overview cache files")

if __name__ == '__main__':
    main()
