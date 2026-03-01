"""VUID Resolution module for early vote roster processing.

DB-first approach: resolves VUIDs against the voters table in SQLite,
which is the single source of truth for voter registration data,
addresses, and geocoded coordinates.

Falls back to scanning GeoJSON map_data files only for VUIDs not in the DB.
"""
import json
import re
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# Column name aliases mapping canonical names to accepted variations.
# Keys are the canonical (lowercase) column names used internally.
# Values are lists of known variations from different county formats.
COLUMN_ALIASES = {
    'vuid': [
        'VUID', 'Vuid', 'VOTER_ID', 'VoterID', 'ID',
        'State ID', 'STATE ID', 'StateID', 'STATE_ID', 'State Id',
        'SOS VUID', 'SOS_VUID', 'SOSVUID',
        'Voter ID', 'VOTER ID', 'VoterId',
        'CERT', 'Cert', 'Certificate',
    ],
    'voter_name': [
        'VoterName', 'Voter Name', 'VOTER NAME', 'NAME', 'VOTER_NAME',
        'Voter', 'FULL NAME', 'Full Name', 'FullName', 'FULL_NAME',
    ],
    'lastname': [
        'LASTNAME', 'LastName', 'Last Name', 'LAST NAME', 'LAST_NAME',
        'Last', 'LAST', 'Surname', 'SURNAME',
    ],
    'firstname': [
        'FIRSTNAME', 'FirstName', 'First Name', 'FIRST NAME', 'FIRST_NAME',
        'First', 'FIRST', 'Given Name', 'GIVEN NAME',
    ],
    'middlename': [
        'MIDDLENAME', 'MiddleName', 'Middle Name', 'MIDDLE NAME', 'MIDDLE_NAME',
        'Middle', 'MIDDLE', 'MI',
    ],
    'suffix': [
        'SUFFIX', 'Suffix', 'Name Suffix', 'NAME SUFFIX',
    ],
    'party': [
        'PARTY', 'Party', 'PARTY_VOTED', 'PartyVoted',
        'Check-In Party', 'CHECK-IN PARTY', 'CHECKIN PARTY', 'CheckIn Party',
        'Check In Party', 'CHECK IN PARTY', 'CHECKIN_PARTY', 'CHECK_IN_PARTY',
        'Party Voted', 'PARTY VOTED', 'Ballot Party', 'BALLOT PARTY',
        'Primary Party', 'PRIMARY PARTY', 'PRIMARY_PARTY',
        'Party Code', 'PARTY CODE', 'PARTY_CODE',
        'Political Party', 'POLITICAL PARTY',
    ],
    'precinct': [
        'PRECINCT', 'Precinct', 'PCT', 'PREC', 'Pct', 'Prec',
        'Precinct Number', 'PRECINCT NUMBER', 'PRECINCT_NUMBER',
        'Precinct No', 'PRECINCT NO', 'Pct No', 'PCT NO',
        'Voting Precinct', 'VOTING PRECINCT',
    ],
    'address': [
        'ADDRESS', 'Address', 'STREET', 'Street',
        'FULL_ADDRESS', 'FullAddress', 'ADDR',
        'RESIDENTIAL_ADDRESS', 'RES_ADDRESS', 'Residential Address',
        'Res Address', 'RES ADDRESS', 'Street Address', 'STREET ADDRESS',
        'Mailing Address', 'MAILING ADDRESS',
        'Physical Address', 'PHYSICAL ADDRESS',
    ],
    'city': [
        'CITY', 'City', 'TOWN', 'Town', 'Residence City', 'RESIDENCE CITY',
    ],
    'zip': [
        'ZIP', 'Zip', 'ZIP CODE', 'Zip Code', 'ZIPCODE', 'ZipCode',
        'ZIP_CODE', 'Postal Code', 'POSTAL CODE',
    ],
    'county': [
        'COUNTY', 'County', 'COUNTY_NAME', 'County Name', 'COUNTY NAME',
    ],
    'ballot_style': [
        'BALLOT STYLE', 'Ballot Style', 'BALLOT_STYLE', 'BallotStyle',
        'Ballot', 'BALLOT', 'Style', 'STYLE',
    ],
    'check_in': [
        'CHECK-IN', 'Check-In', 'CHECKIN', 'CheckIn', 'Check In', 'CHECK IN',
        'CHECK_IN', 'Check-in Date', 'CHECK-IN DATE',
        'Check-In Time', 'CHECK-IN TIME', 'Checked In', 'CHECKED IN',
    ],
    'site': [
        'SITE', 'Site', 'LOCATION', 'Location', 'POLLING PLACE', 'Polling Place',
        'Vote Site', 'VOTE SITE', 'VOTE_SITE', 'Voting Location', 'VOTING LOCATION',
        'EV Site', 'EV SITE', 'EV_SITE',
    ],
    'sex': [
        'SEX', 'Sex', 'GENDER', 'Gender', 'M/F',
    ],
    'birth_year': [
        'BIRTH_YEAR', 'BirthYear', 'Birth Year', 'BIRTH YEAR',
        'DOB', 'Dob', 'DATE OF BIRTH', 'Date of Birth', 'DATE_OF_BIRTH',
        'YOB', 'Year of Birth', 'YEAR OF BIRTH',
    ],
    'registration_date': [
        'REGISTRATION_DATE', 'Registration Date', 'REGISTRATION DATE',
        'REG DATE', 'Reg Date', 'REG_DATE', 'Date Registered', 'DATE REGISTERED',
    ],
}

# Address column names to detect standard (non-early-vote) uploads
ADDRESS_ALIASES = [
    'ADDRESS', 'Address', 'address', 'STREET', 'Street', 'street',
    'FULL_ADDRESS', 'full_address', 'FullAddress', 'ADDR', 'addr',
    'RESIDENTIAL_ADDRESS', 'residential_address', 'RES_ADDRESS',
    'RES ADDRESS', 'Res Address', 'Residential Address',
    'STREET ADDRESS', 'Street Address', 'Physical Address', 'PHYSICAL ADDRESS',
    'Mailing Address', 'MAILING ADDRESS',
]


def normalize_column_names(df: pd.DataFrame, custom_mappings: dict = None) -> pd.DataFrame:
    """Rename DataFrame columns to canonical names using COLUMN_ALIASES.
    
    Uses case-insensitive matching with whitespace/underscore normalization
    to handle variations across different county formats.
    
    Args:
        df: DataFrame with original column names
        custom_mappings: Optional dict of {source_column: canonical_column} from saved county mappings.
                         These take priority over COLUMN_ALIASES.
    """
    # Build a lookup: normalized_key → canonical_name
    # Normalization: uppercase, strip, replace spaces/hyphens/underscores
    def _norm(s):
        return re.sub(r'[\s_\-]+', '', str(s).strip().upper())

    alias_lookup = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lookup[_norm(alias)] = canonical

    rename_map = {}
    
    # First apply custom mappings (highest priority)
    if custom_mappings:
        for col in df.columns:
            if col in custom_mappings and custom_mappings[col]:
                canonical = custom_mappings[col]
                if canonical not in df.columns or canonical == col:
                    rename_map[col] = canonical
    
    # PASS 1: Map columns whose normalized name exactly matches a canonical name.
    # This ensures that e.g. "VUID" always maps to "vuid" even if "Certificate"
    # (an alias for vuid) appears first in the DataFrame.
    canonical_names_normed = {_norm(c): c for c in COLUMN_ALIASES.keys()}
    for col in df.columns:
        if col in rename_map:
            continue
        normed = _norm(col)
        if normed in canonical_names_normed:
            canonical = canonical_names_normed[normed]
            mapped_targets = set(rename_map.values())
            if (canonical not in df.columns or canonical == col) and canonical not in mapped_targets:
                rename_map[col] = canonical
    
    # PASS 2: Map remaining columns via alias lookup
    for col in df.columns:
        if col in rename_map:
            continue  # Already mapped by custom mapping or pass 1
        normed = _norm(col)
        if normed in alias_lookup:
            canonical = alias_lookup[normed]
            # Don't rename if it would collide with an existing column or already-mapped target
            mapped_targets = set(rename_map.values())
            if (canonical not in df.columns or canonical == col) and canonical not in mapped_targets:
                rename_map[col] = canonical

    if rename_map:
        logger.info(f"Column normalization: {rename_map}")

    return df.rename(columns=rename_map)


def preview_column_mapping(columns: list, custom_mappings: dict = None) -> dict:
    """Preview how columns would be mapped without actually renaming.
    
    Returns a dict with:
        - mapped: {source_col: canonical_col} for auto-resolved columns
        - unmapped: [source_col, ...] for columns that couldn't be resolved
        - canonical_options: list of all canonical column names available
    """
    def _norm(s):
        return re.sub(r'[\s_\-]+', '', str(s).strip().upper())

    alias_lookup = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lookup[_norm(alias)] = canonical

    mapped = {}
    unmapped = []

    # Apply custom mappings first
    if custom_mappings:
        for col in columns:
            if col in custom_mappings and custom_mappings[col]:
                mapped[col] = custom_mappings[col]

    # Then auto-map remaining
    for col in columns:
        if col in mapped:
            continue
        normed = _norm(col)
        if normed in alias_lookup:
            mapped[col] = alias_lookup[normed]
        else:
            unmapped.append(col)

    return {
        'mapped': mapped,
        'unmapped': unmapped,
        'canonical_options': list(COLUMN_ALIASES.keys()),
    }


def has_vuid_column(df: pd.DataFrame) -> bool:
    """Check if DataFrame has a recognized VUID column."""
    all_vuid_aliases = COLUMN_ALIASES['vuid']
    return any(alias in df.columns for alias in all_vuid_aliases)


def has_address_column(df: pd.DataFrame) -> bool:
    """Check if DataFrame has a recognized ADDRESS column."""
    return any(alias in df.columns for alias in ADDRESS_ALIASES)


def parse_voter_name(name: str) -> tuple:
    """Parse voter name into (lastname, firstname).
    
    Handles formats:
    - "LASTNAME, FIRSTNAME"
    - "FIRSTNAME LASTNAME"
    - Single name (used as lastname)
    """
    if not name or not isinstance(name, str):
        return ('', '')
    
    name = name.strip()
    if not name:
        return ('', '')
    
    if ',' in name:
        parts = name.split(',', 1)
        lastname = parts[0].strip().upper()
        firstname = parts[1].strip().upper() if len(parts) > 1 else ''
        return (lastname, firstname)
    
    parts = name.strip().split()
    if len(parts) >= 2:
        firstname = ' '.join(parts[:-1]).upper()
        lastname = parts[-1].upper()
        return (lastname, firstname)
    
    return (name.upper(), '')


class VUIDResolver:
    """Resolves VUIDs from early vote rosters against the voter database.
    
    Primary source: voters table in SQLite (registration DB)
    Fallback: GeoJSON map_data files (for VUIDs not yet in the DB)
    """
    
    def __init__(self, county: str, data_dir: Path):
        self.county = county
        self.data_dir = Path(data_dir)
        self._geojson_fallback = {}  # only loaded if needed
        self._fallback_loaded = False
        self._db_hits = 0
        self._geojson_hits = 0
        self._misses = 0
    
    @staticmethod
    def normalize_vuid(raw) -> str:
        """Normalize a VUID value. Strips whitespace and trailing .0 from floats."""
        if raw is None:
            return ''
        s = str(raw).strip()
        s = re.sub(r'\.\d*$', '', s)
        return s
    
    def build_lookup(self) -> int:
        """Return count of voters in the DB for this county.
        
        The DB is always available — no need to preload into memory.
        We just return the count for logging purposes.
        """
        import database as db
        conn = db.get_connection()
        row = conn.execute(
            "SELECT COUNT(*) FROM voters WHERE county = ?",
            (self.county,)
        ).fetchone()
        count = row[0] if row else 0
        logger.info(f"Voter DB has {count:,} voters for {self.county} County")
        return count
    
    def _load_geojson_fallback(self):
        """Load GeoJSON map_data files as fallback for VUIDs not in the DB."""
        if self._fallback_loaded:
            return
        self._fallback_loaded = True
        
        if not self.data_dir.exists():
            return
        
        for f in sorted(self.data_dir.glob('map_data_*.json')):
            name_lower = f.name.lower()
            if 'cumulative' in name_lower:
                continue
            if self.county.lower() not in name_lower:
                continue
            try:
                with open(f, 'r') as fh:
                    data = json.load(fh)
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    geom = feature.get('geometry')
                    raw_vuid = props.get('vuid', '')
                    if not raw_vuid:
                        continue
                    normalized = self.normalize_vuid(raw_vuid)
                    if not normalized:
                        continue
                    lat, lng = None, None
                    if geom and geom.get('type') == 'Point' and geom.get('coordinates'):
                        coords = geom['coordinates']
                        if len(coords) >= 2 and coords[0] != 0 and coords[1] != 0:
                            lng, lat = coords[0], coords[1]
                    self._geojson_fallback[normalized] = {
                        'lat': lat,
                        'lng': lng,
                        'address': props.get('address', ''),
                        'display_name': props.get('address', props.get('display_name', '')),
                        'party_affiliation_current': props.get('party_affiliation_current', ''),
                    }
            except Exception as e:
                logger.warning(f"Error reading {f}: {e}")
        
        logger.info(f"GeoJSON fallback loaded: {len(self._geojson_fallback)} VUIDs")
    
    def resolve(self, vuid) -> dict:
        """Look up a single VUID. DB first, GeoJSON fallback.
        
        Returns voter data dict or None if not found anywhere.
        """
        normalized = self.normalize_vuid(vuid)
        if not normalized:
            return None
        
        # Primary: look up in voter DB
        import database as db
        conn = db.get_connection()
        row = conn.execute(
            "SELECT lat, lng, address, geocoded, current_party FROM voters WHERE vuid = ?",
            (normalized,)
        ).fetchone()
        
        if row:
            lat, lng, address, geocoded, current_party = row
            self._db_hits += 1
            result = {
                'lat': lat if geocoded == 1 else None,
                'lng': lng if geocoded == 1 else None,
                'address': address or '',
                'display_name': address or '',
                'party_affiliation_current': current_party or '',
                'source': 'db',
            }
            return result
        
        # Fallback: GeoJSON files
        self._load_geojson_fallback()
        fallback = self._geojson_fallback.get(normalized)
        if fallback:
            self._geojson_hits += 1
            fallback['source'] = 'geojson'
            return fallback
        
        self._misses += 1
        return None
    
    def resolve_batch(self, vuids: list) -> dict:
        """Resolve a batch of VUIDs efficiently. Returns {vuid: data_dict}.
        
        Uses a single DB query for the batch, then falls back to GeoJSON
        for any that weren't found.
        """
        import database as db
        conn = db.get_connection()
        results = {}
        
        # Normalize all VUIDs
        normalized = [(self.normalize_vuid(v), v) for v in vuids]
        clean_vuids = [n for n, _ in normalized if n]
        
        # Batch DB lookup
        if clean_vuids:
            placeholders = ','.join('?' * len(clean_vuids))
            rows = conn.execute(
                f"SELECT vuid, lat, lng, address, geocoded, current_party, sex, birth_year, "
                f"firstname, lastname, precinct "
                f"FROM voters WHERE vuid IN ({placeholders})",
                clean_vuids
            ).fetchall()
            
            db_map = {}
            for row in rows:
                vuid, lat, lng, address, geocoded, current_party, sex, birth_year, firstname, lastname, precinct = row
                db_map[vuid] = {
                    'lat': lat if geocoded == 1 else None,
                    'lng': lng if geocoded == 1 else None,
                    'address': address or '',
                    'display_name': address or '',
                    'party_affiliation_current': current_party or '',
                    'sex': sex or '',
                    'birth_year': birth_year or 0,
                    'firstname': firstname or '',
                    'lastname': lastname or '',
                    'precinct': precinct or '',
                    'source': 'db',
                }
            
            self._db_hits += len(db_map)
            
            # Check GeoJSON fallback for missing ones
            missing = [v for v in clean_vuids if v not in db_map]
            if missing:
                self._load_geojson_fallback()
            
            for norm_vuid in clean_vuids:
                if norm_vuid in db_map:
                    results[norm_vuid] = db_map[norm_vuid]
                elif norm_vuid in self._geojson_fallback:
                    self._geojson_hits += 1
                    fb = dict(self._geojson_fallback[norm_vuid])
                    fb['source'] = 'geojson'
                    results[norm_vuid] = fb
                else:
                    self._misses += 1
        
        return results
    
    def get_stats(self) -> dict:
        """Return resolution statistics."""
        total = self._db_hits + self._geojson_hits + self._misses
        return {
            'total_resolved': self._db_hits + self._geojson_hits,
            'db_hits': self._db_hits,
            'geojson_hits': self._geojson_hits,
            'misses': self._misses,
            'total_attempted': total,
            'db_hit_rate': f"{self._db_hits/total*100:.1f}%" if total > 0 else "0%",
        }
