"""VUID Resolution module for early vote roster processing.

Matches VUIDs from early vote rosters against existing processed GeoJSON
datasets to recover address, geocoded coordinates, and party information.
"""
import json
import re
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Column name aliases mapping canonical names to accepted variations
COLUMN_ALIASES = {
    'voter_name': ['VoterName', 'Voter Name', 'VOTER NAME', 'NAME', 'VOTER_NAME'],
    'vuid': ['VUID', 'Vuid', 'VOTER_ID', 'VoterID', 'ID'],
    'precinct': ['PRECINCT', 'Precinct', 'PCT', 'PREC'],
}

# Address column names to detect standard (non-early-vote) uploads
ADDRESS_ALIASES = [
    'ADDRESS', 'Address', 'address', 'STREET', 'Street', 'street',
    'FULL_ADDRESS', 'full_address', 'FullAddress', 'ADDR', 'addr',
    'RESIDENTIAL_ADDRESS', 'residential_address', 'RES_ADDRESS',
]


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Rename DataFrame columns to canonical names using COLUMN_ALIASES.
    
    Unrecognized columns remain unchanged.
    """
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = canonical
                break
    return df.rename(columns=rename_map)


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
    
    # Format: "LASTNAME, FIRSTNAME"
    if ',' in name:
        parts = name.split(',', 1)
        lastname = parts[0].strip().upper()
        firstname = parts[1].strip().upper() if len(parts) > 1 else ''
        return (lastname, firstname)
    
    # Format: "FIRSTNAME LASTNAME" (split on last space)
    parts = name.strip().split()
    if len(parts) >= 2:
        firstname = ' '.join(parts[:-1]).upper()
        lastname = parts[-1].upper()
        return (lastname, firstname)
    
    # Single name
    return (name.upper(), '')


class VUIDResolver:
    """Resolves VUIDs from early vote rosters against existing datasets.
    
    Scans GeoJSON map_data files for the same county to build a VUID lookup,
    then resolves individual VUIDs to recover address/coordinate data.
    """
    
    def __init__(self, county: str, data_dir: Path):
        self.county = county.lower()
        self.data_dir = Path(data_dir)
        self.vuid_lookup = {}  # normalized_vuid -> voter data dict
    
    @staticmethod
    def normalize_vuid(raw) -> str:
        """Normalize a VUID value.
        
        Strips whitespace and trailing decimal portions.
        Examples:
            "2141860923.0" -> "2141860923"
            " 2141860923 " -> "2141860923"
        """
        if raw is None:
            return ''
        s = str(raw).strip()
        # Remove trailing decimal portion (e.g., ".0", ".00")
        s = re.sub(r'\.\d*$', '', s)
        return s
    
    def build_lookup(self) -> int:
        """Scan all existing GeoJSON files for the same county.
        
        Builds vuid_lookup dict. When a VUID appears in multiple datasets,
        keeps the record from the most recently dated file.
        
        Returns the number of unique VUIDs in the lookup.
        """
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            return 0
        
        # Find all map_data files for this county
        pattern = f"map_data_*.json"
        files = sorted(self.data_dir.glob(pattern))
        
        # Filter to same county and sort by date (filename contains date)
        county_files = []
        for f in files:
            name_lower = f.name.lower()
            # Skip cumulative files
            if 'cumulative' in name_lower:
                continue
            # Check county match (case-insensitive)
            # Filename format: map_data_{County}_{Year}_{electionType}_{party}_{date}.json
            parts = f.stem.split('_')
            if len(parts) >= 3:
                file_county = parts[2].lower()  # map_data_{County}
                if file_county == self.county:
                    # Extract date from filename for sorting
                    date_part = parts[-1] if len(parts) >= 4 else '00000000'
                    county_files.append((date_part, f))
        
        # Sort by date ascending so later files overwrite earlier ones
        county_files.sort(key=lambda x: x[0])
        
        logger.info(f"Found {len(county_files)} datasets for county '{self.county}'")
        
        for date_part, filepath in county_files:
            try:
                with open(filepath, 'r') as fh:
                    data = json.load(fh)
                
                features = data.get('features', [])
                loaded = 0
                for feature in features:
                    props = feature.get('properties', {})
                    geom = feature.get('geometry')
                    
                    # Get VUID from properties
                    raw_vuid = props.get('vuid', '')
                    if not raw_vuid:
                        continue
                    
                    normalized = self.normalize_vuid(raw_vuid)
                    if not normalized:
                        continue
                    
                    # Extract coordinates
                    lat, lng = None, None
                    if geom and geom.get('type') == 'Point' and geom.get('coordinates'):
                        coords = geom['coordinates']
                        lng, lat = coords[0], coords[1]
                    
                    # Store in lookup (later files overwrite earlier)
                    self.vuid_lookup[normalized] = {
                        'lat': lat,
                        'lng': lng,
                        'address': props.get('address', ''),
                        'display_name': props.get('address', props.get('display_name', '')),
                        'party_affiliation_current': props.get('party_affiliation_current', ''),
                    }
                    loaded += 1
                
                logger.info(f"Loaded {loaded} VUIDs from {filepath.name}")
                
            except Exception as e:
                logger.warning(f"Error reading {filepath}: {e}")
                continue
        
        logger.info(f"VUID lookup built with {len(self.vuid_lookup)} unique VUIDs")
        return len(self.vuid_lookup)
    
    def resolve(self, vuid) -> dict:
        """Look up a single VUID.
        
        Returns voter data dict or None if not found.
        """
        normalized = self.normalize_vuid(vuid)
        return self.vuid_lookup.get(normalized)
