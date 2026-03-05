"""SQLite database module for voter data management.

Provides a centralized voter profile database that accumulates data from:
- Voter registration files (baseline: name, address, demographics)
- Election day files (voting behavior per election)
- Early vote rosters (early voting participation)

The database replaces JSON-file-based lookups with indexed queries,
dramatically reducing memory usage and improving lookup speed.
"""
import sqlite3
import logging
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from config import Config

logger = logging.getLogger(__name__)

DB_PATH = Config.DATA_DIR / 'whovoted.db'

# Thread-local storage for connections
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=30)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    return _local.conn


@contextmanager
def get_db():
    """Context manager for database operations with auto-commit."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    """Initialize database schema. Safe to call multiple times."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS voters (
                vuid TEXT PRIMARY KEY,
                lastname TEXT,
                firstname TEXT,
                middlename TEXT,
                suffix TEXT,
                address TEXT,
                city TEXT,
                zip TEXT,
                county TEXT,
                birth_year INTEGER,
                registration_date TEXT,
                sex TEXT,
                registered_party TEXT,
                current_party TEXT,
                precinct TEXT,
                lat REAL,
                lng REAL,
                geocoded INTEGER DEFAULT 0,
                source TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS voter_elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vuid TEXT NOT NULL,
                election_date TEXT,
                election_year TEXT,
                election_type TEXT,
                voting_method TEXT,
                party_voted TEXT,
                precinct TEXT,
                ballot_style TEXT,
                site TEXT,
                check_in TEXT,
                source_file TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(vuid, election_date, voting_method)
            );

            CREATE TABLE IF NOT EXISTS geocoding_cache (
                address_key TEXT PRIMARY KEY,
                lat REAL,
                lng REAL,
                display_name TEXT,
                source TEXT,
                cached_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_voters_county ON voters(county);
            CREATE INDEX IF NOT EXISTS idx_voters_precinct ON voters(precinct);
            CREATE INDEX IF NOT EXISTS idx_voters_current_party ON voters(current_party);
            CREATE INDEX IF NOT EXISTS idx_voters_geocoded ON voters(geocoded);
            CREATE INDEX IF NOT EXISTS idx_voters_lastname ON voters(lastname);
            CREATE INDEX IF NOT EXISTS idx_voters_firstname ON voters(firstname);
            CREATE INDEX IF NOT EXISTS idx_voters_birth_year ON voters(birth_year);
            CREATE INDEX IF NOT EXISTS idx_voter_elections_vuid ON voter_elections(vuid);
            CREATE INDEX IF NOT EXISTS idx_voter_elections_date ON voter_elections(election_date);
            CREATE INDEX IF NOT EXISTS idx_voter_elections_party ON voter_elections(party_voted);

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                picture TEXT,
                role TEXT DEFAULT 'pending',
                google_sub TEXT UNIQUE,
                created_at TEXT DEFAULT (datetime('now')),
                approved_at TEXT,
                approved_by TEXT,
                last_login TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

            CREATE TABLE IF NOT EXISTS column_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county TEXT NOT NULL,
                source_column TEXT NOT NULL,
                canonical_column TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(county, source_column)
            );
            CREATE INDEX IF NOT EXISTS idx_column_mappings_county ON column_mappings(county);
        """)
    logger.info(f"Database initialized at {DB_PATH}")
    
    # Migrations — add columns that may not exist in older databases
    _run_migrations()

def _run_migrations():
    """Run schema migrations for columns added after initial release."""
    with get_db() as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(voter_elections)").fetchall()]
        
        # Add vote_date column
        if 'vote_date' not in cols:
            logger.info("Migration: adding vote_date column to voter_elections")
            conn.execute("ALTER TABLE voter_elections ADD COLUMN vote_date TEXT")
        
        # Add data_source column
        if 'data_source' not in cols:
            logger.info("Migration: adding data_source column to voter_elections")
            conn.execute("ALTER TABLE voter_elections ADD COLUMN data_source TEXT DEFAULT ''")
            # Backfill existing records based on source_file patterns
            conn.execute("""
                UPDATE voter_elections SET data_source = 'tx-sos-evr'
                WHERE source_file LIKE 'evr_scraper_%' AND (data_source IS NULL OR data_source = '')
            """)
            conn.execute("""
                UPDATE voter_elections SET data_source = 'county-upload'
                WHERE source_file NOT LIKE 'evr_scraper_%' AND (data_source IS NULL OR data_source = '')
            """)
            logger.info("Migration: backfilled data_source for existing records")
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_voter_elections_vote_date ON voter_elections(vote_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_voter_elections_data_source ON voter_elections(data_source)")
        
        # Optimized indexes for heatmap and stats queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party ON voter_elections(vuid, election_date, party_voted)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_date_method_party ON voter_elections(election_date, voting_method, party_voted)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_county_geocoded ON voters(county, geocoded)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_county_vuid ON voters(county, vuid)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_lat_lng ON voters(lat, lng)")



# ============================================================================
# VOTER OPERATIONS
# ============================================================================

def upsert_voter(vuid: str, data: dict):
    """Insert or update a voter record. Existing fields are NOT overwritten with empty values."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM voters WHERE vuid = ?", (vuid,)).fetchone()
        
        if existing is None:
            conn.execute("""
                INSERT INTO voters (vuid, lastname, firstname, middlename, suffix,
                    address, city, zip, county, birth_year, registration_date,
                    sex, registered_party, current_party, precinct, lat, lng,
                    geocoded, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vuid,
                data.get('lastname', ''),
                data.get('firstname', ''),
                data.get('middlename', ''),
                data.get('suffix', ''),
                data.get('address', ''),
                data.get('city', ''),
                data.get('zip', ''),
                data.get('county', ''),
                data.get('birth_year'),
                data.get('registration_date', ''),
                data.get('sex', ''),
                data.get('registered_party', ''),
                data.get('current_party', ''),
                data.get('precinct', ''),
                data.get('lat'),
                data.get('lng'),
                1 if data.get('lat') is not None else 0,
                data.get('source', ''),
                datetime.now().isoformat()
            ))
        else:
            # Update only non-empty fields (don't overwrite good data with blanks)
            updates = []
            params = []
            for field in ['lastname', 'firstname', 'middlename', 'suffix',
                          'address', 'city', 'zip', 'county', 'birth_year',
                          'registration_date', 'sex', 'registered_party',
                          'current_party', 'precinct', 'source']:
                val = data.get(field)
                if val is not None and val != '':
                    updates.append(f"{field} = ?")
                    params.append(val)
            
            # Always update lat/lng if provided
            if data.get('lat') is not None:
                updates.extend(["lat = ?", "lng = ?", "geocoded = 1"])
                params.extend([data['lat'], data['lng']])
            
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(vuid)
                conn.execute(
                    f"UPDATE voters SET {', '.join(updates)} WHERE vuid = ?",
                    params
                )


def upsert_voters_batch(records: list):
    """Batch insert/update voter records for performance."""
    with get_db() as conn:
        now = datetime.now().isoformat()
        params_list = []
        for data in records:
            vuid = data.get('vuid', '')
            if not vuid:
                continue
            params_list.append((
                vuid,
                data.get('lastname', ''),
                data.get('firstname', ''),
                data.get('middlename', ''),
                data.get('suffix', ''),
                data.get('address', ''),
                data.get('city', ''),
                data.get('zip', ''),
                data.get('county', ''),
                data.get('birth_year'),
                data.get('registration_date', ''),
                data.get('sex', ''),
                data.get('registered_party', ''),
                data.get('current_party', ''),
                data.get('precinct', ''),
                data.get('lat'),
                data.get('lng'),
                1 if data.get('lat') is not None else 0,
                data.get('source', ''),
                now,
            ))
        if params_list:
            conn.executemany("""
                INSERT INTO voters (vuid, lastname, firstname, middlename, suffix,
                    address, city, zip, county, birth_year, registration_date,
                    sex, registered_party, current_party, precinct, lat, lng,
                    geocoded, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vuid) DO UPDATE SET
                    lastname = CASE WHEN excluded.lastname != '' THEN excluded.lastname ELSE voters.lastname END,
                    firstname = CASE WHEN excluded.firstname != '' THEN excluded.firstname ELSE voters.firstname END,
                    middlename = CASE WHEN excluded.middlename != '' THEN excluded.middlename ELSE voters.middlename END,
                    suffix = CASE WHEN excluded.suffix != '' THEN excluded.suffix ELSE voters.suffix END,
                    address = CASE WHEN excluded.address != '' THEN excluded.address ELSE voters.address END,
                    city = CASE WHEN excluded.city != '' THEN excluded.city ELSE voters.city END,
                    zip = CASE WHEN excluded.zip != '' THEN excluded.zip ELSE voters.zip END,
                    county = CASE WHEN excluded.county != '' THEN excluded.county ELSE voters.county END,
                    birth_year = CASE WHEN excluded.birth_year IS NOT NULL THEN excluded.birth_year ELSE voters.birth_year END,
                    registration_date = CASE WHEN excluded.registration_date != '' THEN excluded.registration_date ELSE voters.registration_date END,
                    sex = CASE WHEN excluded.sex != '' THEN excluded.sex ELSE voters.sex END,
                    registered_party = CASE WHEN excluded.registered_party != '' THEN excluded.registered_party ELSE voters.registered_party END,
                    current_party = CASE WHEN excluded.current_party != '' THEN excluded.current_party ELSE voters.current_party END,
                    precinct = CASE WHEN excluded.precinct != '' THEN excluded.precinct ELSE voters.precinct END,
                    lat = CASE WHEN excluded.lat IS NOT NULL THEN excluded.lat ELSE voters.lat END,
                    lng = CASE WHEN excluded.lng IS NOT NULL THEN excluded.lng ELSE voters.lng END,
                    geocoded = CASE WHEN excluded.lat IS NOT NULL THEN 1 ELSE voters.geocoded END,
                    source = CASE WHEN excluded.source != '' THEN excluded.source ELSE voters.source END,
                    updated_at = excluded.updated_at
            """, params_list)


def get_voter(vuid: str) -> dict:
    """Get a voter record by VUID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM voters WHERE vuid = ?", (vuid,)).fetchone()
        return dict(row) if row else None


def get_voter_with_elections(vuid: str) -> dict:
    """Get a voter record with full election history."""
    with get_db() as conn:
        voter = conn.execute("SELECT * FROM voters WHERE vuid = ?", (vuid,)).fetchone()
        if not voter:
            return None
        
        result = dict(voter)
        elections = conn.execute(
            "SELECT * FROM voter_elections WHERE vuid = ? ORDER BY election_date",
            (vuid,)
        ).fetchall()
        result['elections'] = [dict(e) for e in elections]
        return result


def lookup_vuids(vuids: list) -> dict:
    """Batch lookup voters by VUID list. Returns dict of vuid -> voter dict."""
    if not vuids:
        return {}
    
    with get_db() as conn:
        placeholders = ','.join('?' * len(vuids))
        rows = conn.execute(
            f"SELECT * FROM voters WHERE vuid IN ({placeholders})",
            vuids
        ).fetchall()
        return {row['vuid']: dict(row) for row in rows}


# ============================================================================
# ELECTION HISTORY OPERATIONS
# ============================================================================

def record_election_participation(vuid: str, election_data: dict):
    """Record a voter's participation in an election."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO voter_elections (vuid, election_date, election_year,
                election_type, voting_method, party_voted, precinct,
                ballot_style, site, check_in, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vuid, election_date, voting_method) DO UPDATE SET
                party_voted = excluded.party_voted,
                precinct = excluded.precinct,
                ballot_style = excluded.ballot_style,
                site = excluded.site,
                check_in = excluded.check_in,
                source_file = excluded.source_file
        """, (
            vuid,
            election_data.get('election_date', ''),
            election_data.get('election_year', ''),
            election_data.get('election_type', ''),
            election_data.get('voting_method', ''),
            election_data.get('party_voted', ''),
            election_data.get('precinct', ''),
            election_data.get('ballot_style', ''),
            election_data.get('site', ''),
            election_data.get('check_in', ''),
            election_data.get('source_file', '')
        ))


def record_elections_batch(records: list):
    """Batch record election participations."""
    with get_db() as conn:
        params_list = []
        for data in records:
            vuid = data.get('vuid', '')
            if not vuid:
                continue
            params_list.append((
                vuid,
                data.get('election_date', ''),
                data.get('election_year', ''),
                data.get('election_type', ''),
                data.get('voting_method', ''),
                data.get('party_voted', ''),
                data.get('precinct', ''),
                data.get('ballot_style', ''),
                data.get('site', ''),
                data.get('check_in', ''),
                data.get('source_file', ''),
                data.get('vote_date', ''),
                data.get('data_source', ''),
            ))
        if params_list:
            conn.executemany("""
                INSERT INTO voter_elections (vuid, election_date, election_year,
                    election_type, voting_method, party_voted, precinct,
                    ballot_style, site, check_in, source_file, vote_date, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vuid, election_date, voting_method) DO UPDATE SET
                    party_voted = excluded.party_voted,
                    precinct = excluded.precinct,
                    ballot_style = excluded.ballot_style,
                    site = excluded.site,
                    check_in = excluded.check_in,
                    source_file = excluded.source_file,
                    vote_date = CASE WHEN voter_elections.vote_date IS NULL OR voter_elections.vote_date = ''
                                     THEN excluded.vote_date
                                     ELSE voter_elections.vote_date END,
                    data_source = CASE WHEN voter_elections.data_source IS NULL OR voter_elections.data_source = ''
                                       THEN excluded.data_source
                                       ELSE voter_elections.data_source END
            """, params_list)



def get_voter_history(vuid: str) -> list:
    """Get election history for a voter, ordered by date."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM voter_elections WHERE vuid = ? ORDER BY election_date",
            (vuid,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_current_party(vuid: str):
    """Update a voter's current_party based on their most recent election participation."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT party_voted FROM voter_elections
            WHERE vuid = ? AND party_voted != '' AND party_voted IS NOT NULL
            ORDER BY election_date DESC LIMIT 1
        """, (vuid,)).fetchone()
        
        if row and row['party_voted']:
            conn.execute(
                "UPDATE voters SET current_party = ?, updated_at = ? WHERE vuid = ?",
                (row['party_voted'], datetime.now().isoformat(), vuid)
            )


def update_all_current_parties():
    """Bulk update current_party for all voters based on most recent election."""
    with get_db() as conn:
        conn.execute("""
            UPDATE voters SET current_party = (
                SELECT ve.party_voted FROM voter_elections ve
                WHERE ve.vuid = voters.vuid
                    AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
                ORDER BY ve.election_date DESC LIMIT 1
            ), updated_at = ?
            WHERE EXISTS (
                SELECT 1 FROM voter_elections ve
                WHERE ve.vuid = voters.vuid
                    AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
            )
        """, (datetime.now().isoformat(),))
        updated = conn.execute("SELECT changes()").fetchone()[0]
        logger.info(f"Updated current_party for {updated} voters")
        return updated


def detect_flips(election_date: str) -> list:
    """Find voters who switched parties for a given election compared to their previous one."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                ve_current.vuid,
                ve_current.party_voted AS current_party,
                ve_prev.party_voted AS previous_party,
                ve_current.election_date AS current_election,
                ve_prev.election_date AS previous_election
            FROM voter_elections ve_current
            JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
            WHERE ve_current.election_date = ?
                AND ve_prev.election_date = (
                    SELECT MAX(ve2.election_date) FROM voter_elections ve2
                    WHERE ve2.vuid = ve_current.vuid
                        AND ve2.election_date < ve_current.election_date
                        AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                )
                AND ve_current.party_voted != '' AND ve_current.party_voted IS NOT NULL
                AND ve_prev.party_voted != '' AND ve_prev.party_voted IS NOT NULL
                AND ve_current.party_voted != ve_prev.party_voted
        """, (election_date,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================================
# GEOCODING CACHE OPERATIONS
# ============================================================================

def cache_get(address_key: str) -> dict:
    """Look up a geocoded address from cache."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM geocoding_cache WHERE address_key = ?",
            (address_key,)
        ).fetchone()
        return dict(row) if row else None


def cache_put(address_key: str, lat: float, lng: float, display_name: str, source: str = 'aws'):
    """Store a geocoded address in cache."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(address_key) DO UPDATE SET
                lat = excluded.lat, lng = excluded.lng,
                display_name = excluded.display_name,
                source = excluded.source, cached_at = excluded.cached_at
        """, (address_key, lat, lng, display_name, source, datetime.now().isoformat()))


def cache_get_batch(address_keys: list) -> dict:
    """Batch lookup geocoded addresses. Returns dict of key -> {lat, lng, display_name}."""
    if not address_keys:
        return {}
    
    with get_db() as conn:
        results = {}
        # SQLite has a limit on variables, chunk if needed
        chunk_size = 500
        for i in range(0, len(address_keys), chunk_size):
            chunk = address_keys[i:i + chunk_size]
            placeholders = ','.join('?' * len(chunk))
            rows = conn.execute(
                f"SELECT * FROM geocoding_cache WHERE address_key IN ({placeholders})",
                chunk
            ).fetchall()
            for row in rows:
                results[row['address_key']] = dict(row)
        return results


def cache_put_batch(entries: list):
    """Batch store geocoded addresses."""
    with get_db() as conn:
        for entry in entries:
            conn.execute("""
                INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(address_key) DO UPDATE SET
                    lat = excluded.lat, lng = excluded.lng,
                    display_name = excluded.display_name,
                    source = excluded.source, cached_at = excluded.cached_at
            """, (
                entry['address_key'], entry['lat'], entry['lng'],
                entry.get('display_name', ''), entry.get('source', 'aws'),
                datetime.now().isoformat()
            ))


def migrate_json_cache(json_cache_path: str):
    """Migrate existing geocoding_cache.json into the SQLite database."""
    import json
    
    cache_path = Path(json_cache_path)
    if not cache_path.exists():
        logger.info("No JSON geocoding cache to migrate")
        return 0
    
    with open(cache_path, 'r') as f:
        cache_data = json.load(f)
    
    count = 0
    batch = []
    for address_key, entry in cache_data.items():
        if isinstance(entry, dict):
            lat = entry.get('lat')
            lng = entry.get('lng')
            display_name = entry.get('display_name', '')
        elif isinstance(entry, list) and len(entry) >= 2:
            lat, lng = entry[0], entry[1]
            display_name = ''
        else:
            continue
        
        if lat is not None and lng is not None:
            batch.append({
                'address_key': address_key,
                'lat': lat,
                'lng': lng,
                'display_name': display_name,
                'source': 'migrated'
            })
            count += 1
        
        if len(batch) >= 1000:
            cache_put_batch(batch)
            batch = []
    
    if batch:
        cache_put_batch(batch)
    
    logger.info(f"Migrated {count} geocoding cache entries to SQLite")
    return count


# ============================================================================
# STATS / QUERIES
# ============================================================================

def get_county_registries() -> list:
    """Get a list of counties with voter registries, including stats and upload dates."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                county,
                COUNT(*) as total_voters,
                SUM(CASE WHEN geocoded = 1 THEN 1 ELSE 0 END) as geocoded_voters,
                MIN(updated_at) as first_imported,
                MAX(updated_at) as last_updated
            FROM voters
            WHERE county != '' AND county IS NOT NULL
            GROUP BY county
            ORDER BY total_voters DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_voter_stats(county: str = None) -> dict:
    """Get summary statistics about the voter database."""
    with get_db() as conn:
        where = "WHERE county = ?" if county else ""
        params = (county,) if county else ()
        
        total = conn.execute(f"SELECT COUNT(*) FROM voters {where}", params).fetchone()[0]
        geocoded = conn.execute(f"SELECT COUNT(*) FROM voters {where} {'AND' if county else 'WHERE'} geocoded = 1", params).fetchone()[0]
        
        party_counts = conn.execute(f"""
            SELECT current_party, COUNT(*) as cnt FROM voters {where}
            GROUP BY current_party ORDER BY cnt DESC
        """, params).fetchall()
        
        election_count = conn.execute("SELECT COUNT(DISTINCT election_date) FROM voter_elections").fetchone()[0]
        
        cache_count = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
        
        return {
            'total_voters': total,
            'geocoded_voters': geocoded,
            'ungeocoded_voters': total - geocoded,
            'party_breakdown': {r['current_party'] or 'Unknown': r['cnt'] for r in party_counts},
            'elections_tracked': election_count,
            'geocoding_cache_size': cache_count
        }

def get_county_registries() -> list:
    """Get a list of counties with voter registries, including stats and upload dates."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                county,
                COUNT(*) as total_voters,
                SUM(CASE WHEN geocoded = 1 THEN 1 ELSE 0 END) as geocoded_voters,
                MIN(updated_at) as first_imported,
                MAX(updated_at) as last_updated
            FROM voters
            WHERE county != '' AND county IS NOT NULL
            GROUP BY county
            ORDER BY total_voters DESC
        """).fetchall()
        return [dict(r) for r in rows]


def generate_geojson_for_election(county: str, election_date: str, party: str = None,
                                  voting_method: str = None) -> dict:
    """Generate GeoJSON FeatureCollection from DB for a specific election.
    
    Joins voter_elections with voters to get coordinates, addresses, and
    party history. This is the DB-first approach — GeoJSON is an output
    format, not the storage layer.
    
    Args:
        county: County name
        election_date: Election date (YYYY-MM-DD)
        party: Optional party filter ('Democratic', 'Republican')
        voting_method: Optional voting method filter ('early-voting', 'election-day')
    
    Returns:
        GeoJSON FeatureCollection dict
    """
    with get_db() as conn:
        query = """
            SELECT 
                v.vuid, v.firstname, v.lastname, v.middlename, v.suffix,
                v.address, v.city, v.zip, v.precinct as reg_precinct,
                v.lat, v.lng, v.geocoded, v.current_party, v.sex, v.birth_year,
                ve.election_date, ve.election_year, ve.election_type,
                ve.voting_method, ve.party_voted, ve.precinct as vote_precinct,
                ve.ballot_style, ve.site, ve.check_in
            FROM voter_elections ve
            INNER JOIN voters v ON ve.vuid = v.vuid
            WHERE v.county = ? AND ve.election_date = ?
        """
        params = [county, election_date]
        
        if party:
            query += " AND ve.party_voted = ?"
            params.append(party)
        if voting_method:
            query += " AND ve.voting_method = ?"
            params.append(voting_method)
        
        rows = conn.execute(query, params).fetchall()
        
        # Pre-fetch VUIDs that have ANY election record before this one
        # A voter is "new" if they have never appeared in any prior election file
        prior_vuids_rows = conn.execute("""
            SELECT DISTINCT vuid FROM voter_elections
            WHERE election_date < ? AND party_voted != '' AND party_voted IS NOT NULL
        """, (election_date,)).fetchall()
        prior_vuids = set(r[0] for r in prior_vuids_rows)
        
        features = []
        for row in rows:
            r = dict(row)
            lat = r['lat']
            lng = r['lng']
            geocoded = r['geocoded']
            
            if geocoded == 1 and lat and lng:
                geometry = {'type': 'Point', 'coordinates': [lng, lat]}
            else:
                geometry = None
            
            name_parts = [r['firstname'] or '', r['middlename'] or '', r['lastname'] or '']
            if r['suffix']:
                name_parts.append(r['suffix'])
            name = ' '.join(p for p in name_parts if p).strip()
            
            # Get party history for context display
            history = conn.execute("""
                SELECT DISTINCT party_voted, election_date
                FROM voter_elections
                WHERE vuid = ? AND party_voted != '' AND party_voted IS NOT NULL
                ORDER BY election_date
            """, (r['vuid'],)).fetchall()
            
            party_history = [{'party': h['party_voted'], 'date': h['election_date']} for h in history]
            
            # Build unique party-per-election-date list
            parties_by_date = []
            seen_dates = set()
            for h in history:
                if h['election_date'] not in seen_dates:
                    seen_dates.add(h['election_date'])
                    parties_by_date.append((h['election_date'], h['party_voted']))
            
            # Flip detection: only flag if THIS election's party differs from
            # the IMMEDIATELY PRECEDING election's party.
            # e.g. D(2022) → R(2024) → R(2026): flip in 2024 only, not 2026
            current_party_in_election = r['party_voted'] or ''
            prev_party = ''
            has_switched = False
            
            for date, party in parties_by_date:
                if date == election_date:
                    break
                prev_party = party  # keep updating until we hit current election
            
            if prev_party and current_party_in_election and prev_party != current_party_in_election:
                has_switched = True
            
            # New voter detection using conservative two-rule approach:
            # Rule 1: Voter was under 18 for all prior elections (newly eligible)
            # Rule 2: County has 3+ prior elections AND voter has no prior history
            is_new_voter = False
            
            if r['vuid'] not in prior_vuids:
                # No prior voting history - check if we can confidently call them "new"
                
                # Rule 1: Was voter under 18 for all prior elections?
                if r['birth_year']:
                    was_eligible_before = _was_eligible_in_prior_elections(
                        conn, r['vuid'], r['birth_year'], election_date
                    )
                    if not was_eligible_before:
                        # Voter was too young before, now eligible - definitely new
                        is_new_voter = True
                
                # Rule 2: Does county have 3+ prior elections?
                if not is_new_voter:
                    has_sufficient_history = _county_has_sufficient_history(conn, county, election_date)
                    if has_sufficient_history:
                        # County has good data, voter never appeared - new voter
                        is_new_voter = True
                
                # If neither rule applies, is_new_voter stays False (better safe than sorry)
            
            props = {
                'vuid': r['vuid'],
                'name': name,
                'lastname': r['lastname'] or '',
                'firstname': r['firstname'] or '',
                'precinct': r['vote_precinct'] or r['reg_precinct'] or '',
                'address': r['address'] or '',
                'display_name': r['address'] or '',
                'original_address': r['address'] or '',
                'party_affiliation_current': r['party_voted'] or r['current_party'] or '',
                'party_affiliation_previous': prev_party,
                'has_switched_parties': has_switched,
                'is_new_voter': is_new_voter,
                'party_history': party_history,
                'ballot_style': r['ballot_style'] or '',
                'site': r['site'] or '',
                'check_in': r['check_in'] or '',
                'voted_in_current_election': True,
                'is_registered': True,
                'unmatched': geometry is None,
                'sex': r['sex'] or '',
                'birth_year': r['birth_year'] or 0,
            }
            
            # Add early vote day if applicable
            if voting_method and 'early' in voting_method.lower():
                props['early_vote_day'] = r['election_date']
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': props,
            })
        
        return {
            'type': 'FeatureCollection',
            'features': features,
        }


def get_election_datasets(county: str = None) -> list:
    """Get election datasets from the DB — replaces metadata JSON file scanning.
    
    Optimized for large databases with statewide data (1M+ records).
    Uses a pre-built summary table that's refreshed on data import.
    Falls back to a direct query if the summary table doesn't exist.
    """
    with get_db() as conn:
        # Ensure summary table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS election_summary (
                election_date TEXT,
                election_year TEXT,
                election_type TEXT,
                voting_method TEXT,
                party_voted TEXT,
                county TEXT,
                total_voters INTEGER,
                geocoded_count INTEGER,
                last_updated TEXT,
                PRIMARY KEY (election_date, party_voted, voting_method, county)
            )
        """)
        
        # Check if summary is populated
        summary_count = conn.execute("SELECT COUNT(*) FROM election_summary").fetchone()[0]
        if summary_count == 0:
            _rebuild_election_summary(conn)
        
        where = "WHERE 1=1"
        params = []
        if county:
            where += " AND county = ?"
            params.append(county)
        
        rows = conn.execute(f"""
            SELECT * FROM election_summary
            {where}
            ORDER BY election_date DESC, party_voted, voting_method
        """, params).fetchall()
        
        results = []
        for r in rows:
            results.append({
                'election_date': r['election_date'],
                'election_year': r['election_year'],
                'election_type': r['election_type'],
                'voting_method': r['voting_method'],
                'party_voted': r['party_voted'],
                'source_file': '',
                'county': r['county'] or 'Unknown',
                'total_voters': r['total_voters'],
                'geocoded_count': r['geocoded_count'],
                'ungeocoded_count': r['total_voters'] - r['geocoded_count'],
                'first_imported': r['last_updated'],
                'last_updated': r['last_updated'],
            })
        return results


def _rebuild_election_summary(conn=None):
    """Rebuild the election_summary table from voter_elections + voters.
    
    Called after data imports to keep the summary fresh.
    """
    should_close = False
    if conn is None:
        conn = get_db().__enter__()
        should_close = True
    
    try:
        conn.execute("DELETE FROM election_summary")
        conn.execute("""
            INSERT INTO election_summary
                (election_date, election_year, election_type, voting_method,
                 party_voted, county, total_voters, geocoded_count, last_updated)
            SELECT 
                ve.election_date,
                ve.election_year,
                ve.election_type,
                ve.voting_method,
                ve.party_voted,
                v.county,
                COUNT(*) as total_voters,
                SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded_count,
                MAX(ve.created_at) as last_updated
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
            GROUP BY ve.election_date, ve.party_voted, ve.voting_method, v.county
        """)
        conn.commit()
        logger.info("Rebuilt election_summary table")
    except Exception as e:
        logger.error(f"Failed to rebuild election_summary: {e}")
    finally:
        if should_close:
            pass  # context manager handles it


def refresh_election_summary():
    """Public API to refresh the election summary after data changes."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS election_summary (
                election_date TEXT,
                election_year TEXT,
                election_type TEXT,
                voting_method TEXT,
                party_voted TEXT,
                county TEXT,
                total_voters INTEGER,
                geocoded_count INTEGER,
                last_updated TEXT,
                PRIMARY KEY (election_date, party_voted, voting_method, county)
            )
        """)
        _rebuild_election_summary(conn)


def get_election_summary() -> dict:
    """Get a high-level summary of all election data in the DB, including per-election flip counts."""
    with get_db() as conn:
        total_records = conn.execute("SELECT COUNT(*) FROM voter_elections").fetchone()[0]
        unique_voters = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections").fetchone()[0]
        election_dates = conn.execute(
            "SELECT DISTINCT election_date FROM voter_elections ORDER BY election_date"
        ).fetchall()
        dates = [r[0] for r in election_dates]
        
        # Overall flip/flip-flop counts (across full history)
        voters_multi = conn.execute("""
            SELECT vuid, GROUP_CONCAT(party_voted || '|' || election_date, ',') as history
            FROM (
                SELECT DISTINCT vuid, party_voted, election_date 
                FROM voter_elections 
                WHERE party_voted != '' AND party_voted IS NOT NULL
                ORDER BY election_date
            )
            GROUP BY vuid
            HAVING COUNT(DISTINCT election_date) >= 2
        """).fetchall()
        
        flips = 0
        flip_flops = 0
        for vuid, history_str in voters_multi:
            entries = history_str.split(',')
            parties_by_date = []
            for entry in entries:
                parts = entry.split('|')
                if len(parts) == 2:
                    parties_by_date.append((parts[1], parts[0]))
            parties_by_date.sort()
            seen = set()
            unique = []
            for date, party in parties_by_date:
                if date not in seen:
                    seen.add(date)
                    unique.append(party)
            switches = sum(1 for i in range(1, len(unique)) if unique[i] != unique[i-1])
            if switches >= 2:
                flip_flops += 1
            elif switches == 1:
                flips += 1
        
        # Per-election flip counts using detect_flips logic
        per_election_flips = {}
        for d in dates:
            flip_rows = conn.execute("""
                SELECT COUNT(*) FROM voter_elections ve_current
                JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
                WHERE ve_current.election_date = ?
                    AND ve_prev.election_date = (
                        SELECT MAX(ve2.election_date) FROM voter_elections ve2
                        WHERE ve2.vuid = ve_current.vuid
                            AND ve2.election_date < ve_current.election_date
                            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                    )
                    AND ve_current.party_voted != '' AND ve_current.party_voted IS NOT NULL
                    AND ve_prev.party_voted != '' AND ve_prev.party_voted IS NOT NULL
                    AND ve_current.party_voted != ve_prev.party_voted
            """, (d,)).fetchone()[0]
            per_election_flips[d] = flip_rows
        
        return {
            'total_election_records': total_records,
            'unique_voters_voted': unique_voters,
            'election_dates': dates,
            'voters_with_multiple_elections': len(voters_multi),
            'single_flips': flips,
            'flip_flops': flip_flops,
            'total_switchers': flips + flip_flops,
            'per_election_flips': per_election_flips,
        }


def _county_has_sufficient_history(conn, county: str, election_date: str) -> bool:
    """Check if a county has 3+ prior elections to reliably detect new voters.
    
    Used to determine if we can confidently identify first-time voters.
    If a county has fewer than 3 prior elections, we can't reliably distinguish
    between true first-time voters and voters who voted before our data coverage.
    
    Returns True only if county has 3+ distinct prior election dates.
    """
    count = conn.execute("""
        SELECT COUNT(DISTINCT ve.election_date)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
          AND ve.election_date < ?
          AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
    """, (county, election_date)).fetchone()[0]
    return count >= 3
def _county_has_prior_data(conn, county: str, election_date: str) -> bool:
    """Check if a county has any prior election data.

    Used to determine if we can detect new voters for this county.
    Returns True if county has at least one prior election.
    """
    count = conn.execute("""
        SELECT COUNT(DISTINCT ve.election_date)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
          AND ve.election_date < ?
          AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
    """, (county, election_date)).fetchone()[0]
    return count > 0





def _was_eligible_in_prior_elections(conn, vuid: str, birth_year: int, election_date: str) -> bool:
    """Check if voter was 18+ during any prior election.
    
    Returns True if voter was eligible (18+) in at least one prior election.
    Returns False if voter was under 18 for all prior elections (newly eligible).
    """
    if not birth_year:
        return True  # Unknown age - assume they were eligible
    
    # Get earliest prior election
    earliest = conn.execute("""
        SELECT MIN(election_date)
        FROM voter_elections
        WHERE election_date < ?
          AND party_voted != '' AND party_voted IS NOT NULL
    """, [election_date]).fetchone()[0]
    
    if not earliest:
        return False  # No prior elections exist
    
    earliest_year = int(earliest.split('-')[0])
    age_at_earliest = earliest_year - birth_year
    
    return age_at_earliest >= 18


def get_election_stats(county: str, election_date: str, party: str = None,
                       voting_method: str = None) -> dict:
    """Get aggregate stats for an election directly from the DB.

    Returns total voters, party breakdown, flip counts, new voter count —
    everything the stats box needs without loading any GeoJSON.
    """
    with get_db() as conn:
        # Base filter
        where = "WHERE v.county = ? AND ve.election_date = ?"
        params = [county, election_date]
        if party:
            where += " AND ve.party_voted = ?"
            params.append(party)
        if voting_method:
            where += " AND ve.voting_method = ?"
            params.append(voting_method)

        # Total voters + party breakdown
        row = conn.execute(f"""
            SELECT
                COUNT(DISTINCT ve.vuid) as total,
                COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
                COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep,
                COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            {where}
        """, params).fetchone()

        total = row['total']
        dem = row['dem']
        rep = row['rep']
        geocoded = row['geocoded']

        # Get VUIDs for this election into a temp table for efficient joins
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS _stats_vuids(vuid TEXT PRIMARY KEY)")
        conn.execute("DELETE FROM _stats_vuids")
        vuid_rows = conn.execute(f"""
            SELECT DISTINCT ve.vuid FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            {where}
        """, params).fetchall()
        vuids = [r['vuid'] for r in vuid_rows]
        for i in range(0, len(vuids), 5000):
            chunk = vuids[i:i+5000]
            conn.executemany("INSERT OR IGNORE INTO _stats_vuids(vuid) VALUES(?)", [(v,) for v in chunk])

        # Flip counts — use temp table + correlated subquery (uses idx_ve_vuid_date_party)
        flipped_to_dem = 0
        flipped_to_rep = 0

        flip_rows = conn.execute("""
            SELECT ve_cur.party_voted as cur_party, ve_prev.party_voted as prev_party,
                   COUNT(*) as cnt
            FROM voter_elections ve_cur
            INNER JOIN _stats_vuids t ON ve_cur.vuid = t.vuid
            INNER JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
            WHERE ve_cur.election_date = ?
              AND ve_prev.election_date = (
                  SELECT MAX(ve2.election_date) FROM voter_elections ve2
                  WHERE ve2.vuid = ve_cur.vuid AND ve2.election_date < ?
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
              )
              AND ve_cur.party_voted != ve_prev.party_voted
              AND ve_cur.party_voted != '' AND ve_cur.party_voted IS NOT NULL
              AND ve_prev.party_voted != '' AND ve_prev.party_voted IS NOT NULL
            GROUP BY ve_cur.party_voted, ve_prev.party_voted
        """, [election_date, election_date]).fetchall()

        for fr in flip_rows:
            if fr['cur_party'] == 'Democratic':
                flipped_to_dem += fr['cnt']
            elif fr['cur_party'] == 'Republican':
                flipped_to_rep += fr['cnt']

        # New voters: use conservative two-rule approach
        # Rule 1: Voters who were under 18 for all prior elections (newly eligible)
        # Rule 2: County has 3+ prior elections AND voter has no prior history
        
        has_sufficient_history = _county_has_sufficient_history(conn, county, election_date)
        
        if has_sufficient_history:
            # County has 3+ prior elections - count all voters with no prior history
            new_row = conn.execute("""
                SELECT COUNT(*) as new_count
                FROM _stats_vuids t
                WHERE NOT EXISTS (
                    SELECT 1 FROM voter_elections ve_old
                    WHERE ve_old.vuid = t.vuid
                      AND ve_old.election_date < ?
                      AND ve_old.party_voted != '' AND ve_old.party_voted IS NOT NULL
                )
            """, [election_date]).fetchone()
            new_voters = new_row['new_count']
        else:
            # County has <3 prior elections - only count newly eligible voters (Rule 1)
            # Get earliest prior election to check eligibility
            earliest = conn.execute("""
                SELECT MIN(election_date) FROM voter_elections
                WHERE election_date < ?
                  AND party_voted != '' AND party_voted IS NOT NULL
            """, [election_date]).fetchone()[0]
            
            if earliest:
                earliest_year = int(earliest.split('-')[0])
                # Count voters who were under 18 at earliest election and have no prior history
                new_row = conn.execute("""
                    SELECT COUNT(*) as new_count
                    FROM _stats_vuids t
                    JOIN voters v ON t.vuid = v.vuid
                    WHERE NOT EXISTS (
                        SELECT 1 FROM voter_elections ve_old
                        WHERE ve_old.vuid = t.vuid
                          AND ve_old.election_date < ?
                          AND ve_old.party_voted != '' AND ve_old.party_voted IS NOT NULL
                    )
                    AND v.birth_year IS NOT NULL
                    AND (? - v.birth_year) < 18
                """, [election_date, earliest_year]).fetchone()
                new_voters = new_row['new_count']
            else:
                # No prior elections at all
                new_voters = 0

        conn.execute("DROP TABLE IF EXISTS _stats_vuids")

        return {
            'total': total,
            'democratic': dem,
            'republican': rep,
            'geocoded': geocoded,
            'flipped_to_dem': flipped_to_dem,
            'flipped_to_rep': flipped_to_rep,
            'new_voters': new_voters,
        }



def get_voters_for_election(county: str, election_date: str, party: str = None,
                            voting_method: str = None,
                            bounds: dict = None, limit: int = None) -> list:
    """Get voter records for an election from the DB.
    
    Returns a list of dicts with all fields needed for map rendering.
    Optional bounds filtering: {sw_lat, sw_lng, ne_lat, ne_lng}
    
    This replaces loading GeoJSON files — the DB is the source of truth.
    """
    with get_db() as conn:
        where = "WHERE v.county = ? AND ve.election_date = ?"
        params = [county, election_date]

        if party:
            where += " AND ve.party_voted = ?"
            params.append(party)
        if voting_method:
            where += " AND ve.voting_method = ?"
            params.append(voting_method)
        if bounds:
            where += " AND v.lat BETWEEN ? AND ? AND v.lng BETWEEN ? AND ?"
            params.extend([bounds['sw_lat'], bounds['ne_lat'],
                           bounds['sw_lng'], bounds['ne_lng']])

        query = f"""
            SELECT DISTINCT
                ve.vuid, v.firstname, v.lastname, v.address, v.precinct,
                v.lat, v.lng, v.geocoded, v.sex, v.birth_year,
                ve.party_voted, ve.voting_method, ve.election_date
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            {where}
        """
        if limit:
            query += f" LIMIT {int(limit)}"

        rows = conn.execute(query, params).fetchall()

        # Pre-fetch previous party for flip detection (batch)
        vuids = [r['vuid'] for r in rows]
        prev_party_map = {}
        for i in range(0, len(vuids), 999):
            chunk = vuids[i:i+999]
            ph = ','.join('?' * len(chunk))
            prev_rows = conn.execute(f"""
                SELECT ve.vuid, ve.party_voted
                FROM voter_elections ve
                WHERE ve.vuid IN ({ph})
                  AND ve.election_date = (
                      SELECT MAX(ve2.election_date) FROM voter_elections ve2
                      WHERE ve2.vuid = ve.vuid
                        AND ve2.election_date < ?
                        AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                  )
                  AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
            """, chunk + [election_date]).fetchall()
            for pr in prev_rows:
                prev_party_map[pr['vuid']] = pr['party_voted']

        # Pre-fetch new voter status (batch)
        prior_vuids = set()
        for i in range(0, len(vuids), 999):
            chunk = vuids[i:i+999]
            ph = ','.join('?' * len(chunk))
            prior_rows = conn.execute(f"""
                SELECT DISTINCT vuid FROM voter_elections
                WHERE vuid IN ({ph})
                  AND election_date < ?
                  AND party_voted != '' AND party_voted IS NOT NULL
            """, chunk + [election_date]).fetchall()
            for pr in prior_rows:
                prior_vuids.add(pr['vuid'])

        # Check if this county has prior election data (for new voter detection)
        has_prior = _county_has_prior_data(conn, county, election_date)

        results = []
        for r in rows:
            vuid = r['vuid']
            cur_party = r['party_voted'] or ''
            prev_party = prev_party_map.get(vuid, '')
            has_switched = bool(prev_party and cur_party and prev_party.lower() != cur_party.lower())

            results.append({
                'vuid': vuid,
                'firstname': r['firstname'] or '',
                'lastname': r['lastname'] or '',
                'name': f"{r['firstname'] or ''} {r['lastname'] or ''}".strip(),
                'address': r['address'] or '',
                'precinct': r['precinct'] or '',
                'lat': r['lat'],
                'lng': r['lng'],
                'geocoded': r['geocoded'] == 1,
                'sex': r['sex'] or '',
                'birth_year': r['birth_year'] or 0,
                'county': county,
                'party_affiliation_current': cur_party,
                'party_affiliation_previous': prev_party if has_switched else '',
                'has_switched_parties': has_switched,
                'is_new_voter': (vuid not in prior_vuids) if has_prior else False,
                'voting_method': r['voting_method'] or '',
            })

        return results


def get_voters_at_location(lat: float, lng: float, election_date: str, voting_method: str = None, counties: list = None) -> list:
    """Look up voter(s) at a specific location for a given election.
    
    Strategy: use lat/lng to find one voter, grab their address, then look up
    ALL voters at that address. This handles the case where household members
    get geocoded to slightly different coordinates.
    
    Args:
        lat: Latitude
        lng: Longitude
        election_date: Election date (YYYY-MM-DD)
        voting_method: Optional voting method filter (early-voting, election-day, mail-in)
        counties: Optional list of counties to filter by
    """
    with get_db() as conn:
        tolerance = 0.0001  # ~11 meters
        vm_clause = " AND ve.voting_method = ?" if voting_method else ""
        vm_params = [voting_method] if voting_method else []
        
        # County filter clause
        county_clause = ""
        county_params = []
        if counties:
            placeholders = ','.join('?' * len(counties))
            county_clause = f" AND v.county IN ({placeholders})"
            county_params = counties

        # Step 1: Find the address of a voter near these coordinates
        addr_row = conn.execute(f"""
            SELECT v.address FROM voters v
            JOIN voter_elections ve ON ve.vuid = v.vuid
            WHERE v.lat BETWEEN ? AND ?
              AND v.lng BETWEEN ? AND ?
              AND ve.election_date = ?
              AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
              AND v.address IS NOT NULL AND v.address != ''
              {vm_clause}
              {county_clause}
            LIMIT 1
        """, [lat - tolerance, lat + tolerance, lng - tolerance, lng + tolerance, election_date] + vm_params + county_params).fetchone()

        if not addr_row or not addr_row['address']:
            return []

        # Normalize: strip apartment/unit for building-level match
        import re
        raw_addr = addr_row['address'].strip().upper()
        base_addr = re.sub(r'\b(?:APT|APARTMENT|UNIT|STE|SUITE|#)\s*[A-Z0-9-]+', '', raw_addr).strip()
        base_addr = re.sub(r'\s{2,}', ' ', base_addr).replace(', ,', ',').strip()

        # Step 2: Find ALL voters at this address (including all units in the building)
        rows = conn.execute(f"""
            SELECT DISTINCT
                v.vuid, v.firstname, v.lastname, v.address, v.precinct,
                v.sex, v.birth_year, v.county, ve.party_voted, v.geocoded
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE UPPER(v.address) LIKE ?
              AND ve.election_date = ?
              AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
              {vm_clause}
              {county_clause}
        """, [base_addr + '%', election_date] + vm_params + county_params).fetchall()

        if not rows:
            return []

        vuids = [r['vuid'] for r in rows]

        # Previous party for flip detection
        prev_party_map = {}
        if vuids:
            ph = ','.join('?' * len(vuids))
            prev_rows = conn.execute(f"""
                SELECT ve.vuid, ve.party_voted
                FROM voter_elections ve
                WHERE ve.vuid IN ({ph})
                  AND ve.election_date = (
                      SELECT MAX(ve2.election_date) FROM voter_elections ve2
                      WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                        AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                  )
                  AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
            """, vuids + [election_date]).fetchall()
            for pr in prev_rows:
                prev_party_map[pr['vuid']] = pr['party_voted']

        # New voter detection
        prior_vuids = set()
        if vuids:
            ph = ','.join('?' * len(vuids))
            prior_rows = conn.execute(f"""
                SELECT DISTINCT vuid FROM voter_elections
                WHERE vuid IN ({ph}) AND election_date < ?
                  AND party_voted != '' AND party_voted IS NOT NULL
            """, vuids + [election_date]).fetchall()
            for pr in prior_rows:
                prior_vuids.add(pr['vuid'])

        # Check if county has prior data
        county_set = set(r['county'] for r in rows if r['county'])
        has_prior_map = {}
        for c in county_set:
            has_prior_map[c] = _county_has_prior_data(conn, c, election_date)

        results = []
        for r in rows:
            vuid = r['vuid']
            cur = r['party_voted'] or ''
            prev = prev_party_map.get(vuid, '')
            flipped = bool(prev and cur and prev.lower() != cur.lower())
            county = r['county'] or ''
            is_new = (vuid not in prior_vuids) if has_prior_map.get(county, False) else False
            results.append({
                'vuid': vuid,
                'name': ' '.join(filter(None, [r['firstname'], r['lastname']])),
                'firstname': r['firstname'] or '',
                'lastname': r['lastname'] or '',
                'address': r['address'] or '',
                'precinct': r['precinct'] or '',
                'sex': r['sex'] or '',
                'birth_year': r['birth_year'] or 0,
                'county': county,
                'party_affiliation_current': cur,
                'party_affiliation_previous': prev if flipped else '',
                'has_switched_parties': flipped,
                'is_new_voter': is_new,
            })

        return results


def get_voters_heatmap(county: str, election_date: str, voting_method: str = None) -> list:
    """Get lightweight voter data for heatmap rendering — just coords + minimal flags.

    Returns ~50 bytes per voter instead of ~500, cutting payload by ~90%.
    Optimized: uses temp table + single-pass queries instead of batched loops.
    """
    with get_db() as conn:
        where = "WHERE v.county = ? AND ve.election_date = ? AND ve.party_voted != '' AND ve.party_voted IS NOT NULL AND v.geocoded = 1 AND v.lat IS NOT NULL AND v.lng IS NOT NULL"
        params = [county, election_date]
        if voting_method:
            where += " AND ve.voting_method = ?"
            params.append(voting_method)

        rows = conn.execute(f"""
            SELECT DISTINCT
                ve.vuid, v.lat, v.lng, ve.party_voted, v.sex, v.birth_year
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            {where}
        """, params).fetchall()

        if not rows:
            return []

        vuids = [r['vuid'] for r in rows]

        # Use temp table for efficient bulk lookups
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS _hm_vuids(vuid TEXT PRIMARY KEY)")
        conn.execute("DELETE FROM _hm_vuids")
        # Insert in larger batches for speed
        for i in range(0, len(vuids), 5000):
            chunk = vuids[i:i+5000]
            conn.executemany("INSERT OR IGNORE INTO _hm_vuids(vuid) VALUES(?)", [(v,) for v in chunk])

        # Single query: previous party for flip detection
        # Uses the idx_ve_vuid_date_party index for the correlated subquery
        prev_party_map = {}
        prev_rows = conn.execute("""
            SELECT ve.vuid, ve.party_voted
            FROM voter_elections ve
            INNER JOIN _hm_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = (
                SELECT MAX(ve2.election_date) FROM voter_elections ve2
                WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                  AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
            )
            AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
        """, [election_date]).fetchall()
        for pr in prev_rows:
            prev_party_map[pr['vuid']] = pr['party_voted']

        # Single query: new voter detection
        prior_vuids = set()
        prior_rows = conn.execute("""
            SELECT DISTINCT ve.vuid FROM voter_elections ve
            INNER JOIN _hm_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date < ?
              AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
        """, [election_date]).fetchall()
        for pr in prior_rows:
            prior_vuids.add(pr['vuid'])

        conn.execute("DROP TABLE IF EXISTS _hm_vuids")

        # Check if this county has prior election data (for new voter detection)
        has_prior = _county_has_prior_data(conn, county, election_date)

        results = []
        for r in rows:
            vuid = r['vuid']
            cur = r['party_voted'] or ''
            prev = prev_party_map.get(vuid, '')
            flipped = bool(prev and cur and prev.lower() != cur.lower())
            is_new = (vuid not in prior_vuids) if has_prior else False
            pc = 1 if 'democrat' in cur.lower() else (2 if 'republican' in cur.lower() else 0)
            flags = (1 if flipped else 0) | (2 if is_new else 0)
            entry = [round(r['lng'], 6), round(r['lat'], 6), pc, flags]
            sex = (r['sex'] or '')[0:1].upper()
            by = r['birth_year'] or 0
            if sex or by:
                entry.append(sex)
                entry.append(by)
            results.append(entry)

        return results



def get_registered_not_voted(county: str, election_date: str, bounds: dict = None, limit: int = None) -> list:
    """Get geocoded registered voters who have NOT voted in a specific election."""
    with get_db() as conn:
        where = "WHERE v.county = ? AND v.geocoded = 1 AND v.lat IS NOT NULL AND v.lng IS NOT NULL"
        params = [county]

        # Exclude voters who voted in this election
        where += " AND v.vuid NOT IN (SELECT vuid FROM voter_elections WHERE election_date = ?)"
        params.append(election_date)

        if bounds:
            where += " AND v.lat BETWEEN ? AND ? AND v.lng BETWEEN ? AND ?"
            params.extend([bounds['sw_lat'], bounds['ne_lat'], bounds['sw_lng'], bounds['ne_lng']])

        query = f"""
            SELECT v.vuid, v.firstname, v.lastname, v.address, v.precinct,
                   v.lat, v.lng, v.sex, v.birth_year, v.current_party, v.registered_party, v.county
            FROM voters v
            {where}
        """
        if limit:
            query += f" LIMIT {int(limit)}"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]



# ============================================================================
# COLUMN MAPPING OPERATIONS
# ============================================================================

def get_column_mappings(county: str) -> dict:
    """Get saved column mappings for a county. Returns {source_column: canonical_column}."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT source_column, canonical_column FROM column_mappings WHERE county = ?",
            (county,)
        ).fetchall()
        return {r['source_column']: r['canonical_column'] for r in rows}


def save_column_mappings(county: str, mappings: dict):
    """Save column mappings for a county. mappings = {source_column: canonical_column}.
    Uses INSERT OR REPLACE to update existing mappings."""
    with get_db() as conn:
        for source_col, canonical_col in mappings.items():
            if canonical_col:  # Only save non-empty mappings
                conn.execute(
                    "INSERT OR REPLACE INTO column_mappings (county, source_column, canonical_column, created_at) "
                    "VALUES (?, ?, ?, datetime('now'))",
                    (county, source_col, canonical_col)
                )
        conn.commit()


def delete_column_mappings(county: str):
    """Delete all column mappings for a county."""
    with get_db() as conn:
        conn.execute("DELETE FROM column_mappings WHERE county = ?", (county,))
        conn.commit()

