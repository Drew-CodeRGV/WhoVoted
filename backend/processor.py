"""Data processing pipeline for voter roll CSV files."""
import json
import uuid
import logging
import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config
from geocoder import GeocodingCache, NominatimGeocoder
from vuid_resolver import (
    VUIDResolver, normalize_column_names, has_vuid_column,
    has_address_column, parse_voter_name, COLUMN_ALIASES
)

logger = logging.getLogger(__name__)

def read_data_file(filepath: str) -> pd.DataFrame:
    """
    Read CSV or Excel file into a pandas DataFrame.
    
    Args:
        filepath: Path to the data file (.csv, .xls, or .xlsx)
    
    Returns:
        pandas DataFrame with the data
    
    Raises:
        ValueError: If file format is not supported
        Exception: If file cannot be read
    """
    filepath_lower = filepath.lower()
    
    try:
        if filepath_lower.endswith('.csv'):
            return pd.read_csv(filepath)
        elif filepath_lower.endswith('.xlsx'):
            return pd.read_excel(filepath, engine='openpyxl')
        elif filepath_lower.endswith('.xls'):
            return pd.read_excel(filepath, engine='xlrd')
        else:
            raise ValueError(f"Unsupported file format. Must be .csv, .xls, or .xlsx")
    except Exception as e:
        logger.error(f"Failed to read file {filepath}: {e}")
        raise

class ValidationResult:
    """Result of CSV validation."""
    
    def __init__(self):
        self.valid_count = 0
        self.invalid_count = 0
        self.suspicious_count = 0
        self.errors = []
        self.warnings = []
    
    def add_error(self, row: int, message: str):
        """Add validation error."""
        self.errors.append({'row': row, 'message': message})
        self.invalid_count += 1
    
    def add_warning(self, row: int, message: str):
        """Add validation warning."""
        self.warnings.append({'row': row, 'message': message})
        self.suspicious_count += 1
    
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0


class CrossReferenceEngine:
    """Cross-references voters across election datasets to detect party switches."""

    def __init__(self, county: str, current_election_date: str, data_dir: Path):
        """
        Args:
            county: County name to filter datasets (e.g., "Hidalgo")
            current_election_date: Election date of the dataset being processed (YYYY-MM-DD)
            data_dir: Path to the data directory containing GeoJSON and metadata files
        """
        self.county = county
        self.current_election_date = current_election_date
        self.data_dir = Path(data_dir)

    def find_earlier_datasets(self) -> list:
        """
        Scan data_dir for metadata files matching the same county with earlier election dates.

        Returns:
            List of dicts with keys: metadata_path, map_data_path, election_date,
            sorted by election_date descending (most recent first).
            Skips malformed/unreadable files with a logged warning.
        """
        earlier = []

        for metadata_path in self.data_dir.glob('metadata_*.json'):
            try:
                with open(metadata_path, 'r') as f:
                    meta = json.load(f)

                county = meta.get('county', '')
                election_date = meta.get('election_date', '')

                if not county or not election_date:
                    logger.warning(f"Skipping malformed metadata file (missing county or election_date): {metadata_path}")
                    continue

                # County must match (case-insensitive)
                if county.lower() != self.county.lower():
                    continue

                # Election date must be strictly before current
                if election_date >= self.current_election_date:
                    continue

                # Derive map_data_path by replacing metadata_ prefix with map_data_
                map_data_filename = 'map_data_' + metadata_path.name[len('metadata_'):]
                map_data_path = self.data_dir / map_data_filename

                earlier.append({
                    'metadata_path': metadata_path,
                    'map_data_path': map_data_path,
                    'election_date': election_date
                })

            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Skipping malformed metadata file {metadata_path}: {e}")
                continue

        # Sort by election_date descending (most recent first)
        earlier.sort(key=lambda d: d['election_date'], reverse=True)
        return earlier

    def load_voter_lookup(self, map_data_path: Path) -> dict:
        """
        Load a GeoJSON file and build lookup dicts for voter matching.

        Args:
            map_data_path: Path to the GeoJSON map data file.

        Returns:
            Dict with 'vuid_lookup' (keyed by VUID string -> party string)
            and 'name_coord_lookup' (keyed by (lastname, firstname, round(lat,4), round(lng,4)) -> party string).
        """
        vuid_lookup = {}
        name_coord_lookup = {}

        try:
            with open(map_data_path, 'r') as f:
                geojson = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load GeoJSON file {map_data_path}: {e}")
            return {'vuid_lookup': vuid_lookup, 'name_coord_lookup': name_coord_lookup}

        features = geojson.get('features', [])
        for feature in features:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coords = geometry.get('coordinates', [])

            party = props.get('party_affiliation_current', '')
            vuid = str(props.get('vuid', '')).strip()
            lastname = str(props.get('lastname', '')).strip().upper()
            firstname = str(props.get('firstname', '')).strip().upper()

            # Build VUID lookup (skip empty VUIDs)
            if vuid:
                vuid_lookup[vuid] = party

            # Build name+coord lookup
            if len(coords) >= 2 and lastname and firstname:
                lng = coords[0]
                lat = coords[1]
                key = (lastname, firstname, round(lat, 4), round(lng, 4))
                name_coord_lookup[key] = party

        return {'vuid_lookup': vuid_lookup, 'name_coord_lookup': name_coord_lookup}

    @staticmethod
    def _extract_current_party_from_row(voter_row) -> str:
        """Extract current party affiliation from a voter row (DataFrame row or dict).

        Checks 'party_affiliation_current' first, then falls back to ballot_style / party columns.
        """
        # Direct field
        pac = voter_row.get('party_affiliation_current', '')
        if pac and str(pac).strip():
            return str(pac).strip()

        # Fallback: party column
        party_val = voter_row.get('party', '')
        if party_val and str(party_val).strip():
            code = str(party_val).strip().upper()
            if code in ('D', 'DEM', 'DEMOCRAT', 'DEMOCRATIC'):
                return 'Democratic'
            if code in ('R', 'REP', 'REPUBLICAN'):
                return 'Republican'
            return code

        # Fallback: ballot_style
        ballot = voter_row.get('ballot_style', '')
        if ballot and str(ballot).strip():
            b = str(ballot).strip().upper()
            if 'REP' in b or 'REPUBLICAN' in b:
                return 'Republican'
            if 'DEM' in b or 'DEMOCRAT' in b:
                return 'Democratic'

        return ''

    def get_previous_party(self, voter_row, vuid_lookup: dict, name_coord_lookup: dict) -> str:
        """
        Look up a voter in the earlier dataset.

        1. Try VUID match first.
        2. If no VUID match, try (lastname, firstname, lat, lng) match.
        3. If match found and party differs from current, return earlier party.
        4. If match found but same party, no match, or earlier party is empty, return empty string.

        Args:
            voter_row: A pandas Series or dict-like with keys: vuid, lastname, firstname, lat, lng, etc.
            vuid_lookup: Dict mapping VUID -> party string from earlier dataset.
            name_coord_lookup: Dict mapping (lastname, firstname, lat, lng) -> party string from earlier dataset.

        Returns:
            Earlier party string if different from current, empty string otherwise.
        """
        current_party = self._extract_current_party_from_row(voter_row)
        earlier_party = ''

        # Try VUID match first
        vuid = str(voter_row.get('vuid', '')).strip()
        if vuid and vuid in vuid_lookup:
            earlier_party = vuid_lookup[vuid]
        else:
            # Fallback: name + coordinates
            lastname = str(voter_row.get('lastname', '')).strip().upper()
            firstname = str(voter_row.get('firstname', '')).strip().upper()
            try:
                lat = float(voter_row.get('lat', 0))
                lng = float(voter_row.get('lng', 0))
            except (TypeError, ValueError):
                lat = 0.0
                lng = 0.0

            if lastname and firstname:
                key = (lastname, firstname, round(lat, 4), round(lng, 4))
                if key in name_coord_lookup:
                    earlier_party = name_coord_lookup[key]

        # Return earlier party only if it's non-empty and different from current
        if earlier_party and earlier_party != current_party:
            return earlier_party

        return ''

    def cross_reference(self, df: pd.DataFrame) -> pd.Series:
        """
        Main entry point. For each voter in df, determine party_affiliation_previous.

        Calls find_earlier_datasets(), loads the most recent earlier dataset via
        load_voter_lookup(), then calls get_previous_party() for each row.

        Args:
            df: DataFrame of current voters with columns like vuid, lastname, firstname, lat, lng, etc.

        Returns:
            A pandas Series of previous party strings aligned with df index.
        """
        earlier_datasets = self.find_earlier_datasets()

        if not earlier_datasets:
            logger.info(f"No earlier datasets found for county '{self.county}' before {self.current_election_date}")
            return pd.Series([''] * len(df), index=df.index)

        # Use the most recent earlier dataset (first in the descending-sorted list)
        most_recent = earlier_datasets[0]
        logger.info(
            f"Cross-referencing against earlier dataset: {most_recent['map_data_path'].name} "
            f"(election_date={most_recent['election_date']})"
        )

        lookups = self.load_voter_lookup(most_recent['map_data_path'])
        vuid_lookup = lookups['vuid_lookup']
        name_coord_lookup = lookups['name_coord_lookup']

        logger.info(
            f"Loaded {len(vuid_lookup)} VUID entries and {len(name_coord_lookup)} name+coord entries "
            f"from earlier dataset"
        )

        results = []
        for _, row in df.iterrows():
            prev = self.get_previous_party(row, vuid_lookup, name_coord_lookup)
            results.append(prev)

        return pd.Series(results, index=df.index)


class ProcessingJob:
    """Background job for processing voter roll CSV."""
    
    def __init__(self, csv_path: str, year: str = None, county: str = None, 
                 election_type: str = None, election_date: str = None, voting_method: str = None,
                 original_filename: str = None, primary_party: str = None, job_id: str = None,
                 max_workers: int = 20):
        """
        Initialize processing job.
        
        Args:
            csv_path: Path to uploaded CSV file
            year: Election year for this data
            county: Texas county name
            election_type: Type of election (primary, runoff, general, special, early-voting)
            election_date: Date of the election
            voting_method: Voting method (early-voting or election-day)
            original_filename: Original filename of the uploaded CSV
            primary_party: Primary party affiliation (democratic/republican) for primary elections
            job_id: Unique job identifier (generated if not provided)
            max_workers: Number of parallel workers for geocoding (default: 20)
        """
        self.csv_path = csv_path
        self.year = year or str(datetime.now().year)
        self.county = county or "Unknown"
        self.election_type = election_type or "general"
        self.election_date = election_date
        self.voting_method = voting_method or "early-voting"
        self.original_filename = original_filename or Path(csv_path).name
        self.primary_party = primary_party or ""  # Store primary party (democratic/republican or empty)
        self.job_id = job_id or str(uuid.uuid4())
        self.max_workers = max_workers  # Number of parallel workers for geocoding
        self.status = 'queued'  # queued, running, completed, failed
        self.progress = 0.0  # 0.0 to 1.0
        self.total_records = 0
        self.processed_records = 0
        self.errors = []
        self.log_messages = []
        self.started_at = None
        self.completed_at = None
        
        # Processing results
        self.geocoded_count = 0
        self.failed_count = 0
        self.cache_hits = 0
        
        # Initialize geocoder
        cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
        self.geocoder = NominatimGeocoder(cache)
    
    def log(self, message: str):
        """Add timestamped log message."""
        timestamp = datetime.now().isoformat()
        self.log_messages.append({
            'timestamp': timestamp,
            'message': message
        })
        logger.info(f"[Job {self.job_id}] {message}")
    
    def run(self):
        """Execute processing pipeline."""
        self.status = 'running'
        self.started_at = datetime.now()
        self.log("Processing started")
        
        try:
            # Step 1: Validate CSV
            self.log("Step 1/5: Validating CSV structure...")
            validation_result = self.validate_csv()
            
            if not validation_result.is_valid():
                self.status = 'failed'
                self.log(f"Validation failed with {len(validation_result.errors)} errors")
                for error in validation_result.errors[:10]:  # Show first 10 errors
                    self.log(f"  Row {error['row']}: {error['message']}")
                return
            
            self.log(f"Validation passed: {validation_result.valid_count} valid records")
            if validation_result.suspicious_count > 0:
                self.log(f"Warning: {validation_result.suspicious_count} suspicious records flagged")
            
            # Step 2: Load and clean data
            self.log("Step 2/5: Loading and cleaning addresses...")
            df = read_data_file(self.csv_path)
            self.total_records = len(df)
            
            # Check if this is an early vote roster (VUID but no address)
            if self.detect_early_vote_roster(df):
                self.process_early_vote_roster(df)
                return
            
            df = self.clean_addresses(df)
            self.log(f"Cleaned {len(df)} addresses")
            self.progress = 0.2
            
            # Step 3: Geocode addresses
            self.log("Step 3/5: Geocoding addresses (this may take a while)...")
            geocoded_df = self.geocode_addresses(df)
            self.log(f"Geocoded {self.geocoded_count} addresses, {self.failed_count} failed")
            self.progress = 0.7
            
            # Step 4: Generate output files
            self.log("Step 4/5: Generating output files...")
            self.generate_outputs(geocoded_df)
            self.log("Output files generated successfully")
            self.progress = 0.9
            
            # Step 5: Deploy to public directory
            self.log("Step 5/5: Deploying to public directory...")
            self.deploy_outputs()
            self.log("Deployment complete")
            self.progress = 1.0
            
            # Complete
            self.status = 'completed'
            self.completed_at = datetime.now()
            processing_time = (self.completed_at - self.started_at).total_seconds()
            
            # Get geocoding stats
            stats = self.geocoder.get_stats()
            
            self.log(f"Processing completed successfully in {processing_time:.1f}s")
            self.log(f"Total records: {self.total_records}")
            self.log(f"Geocoded: {self.geocoded_count}")
            self.log(f"Failed: {self.failed_count}")
            self.log(f"Cache hits: {stats['cache_hits']}")
            self.log(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
            self.log(f"API calls: {stats['api_calls']}")
            
        except Exception as e:
            self.status = 'failed'
            self.log(f"Processing failed: {str(e)}")
            logger.exception(f"Processing job {self.job_id} failed")
            raise
    
    def validate_csv(self) -> ValidationResult:
        """Validate CSV structure and content."""
        result = ValidationResult()

        try:
            df = read_data_file(self.csv_path)
        except Exception as e:
            result.add_error(0, f"Failed to read file: {str(e)}")
            return result

        # Early vote rosters have VUID but no ADDRESS — skip standard column checks
        if has_vuid_column(df) and not has_address_column(df):
            self.log("Detected early vote roster (VUID present, no ADDRESS column)")
            result.valid_count = len(df)
            return result

        # Check required columns for standard voter files
        required_columns = ['ADDRESS', 'PRECINCT', 'BALLOT STYLE']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            result.add_error(0, f"Missing required columns: {', '.join(missing_columns)}")
            return result

        # Check for recommended columns
        recommended_columns = [
            'ID', 'VUID', 'CERT', 'LASTNAME', 'FIRSTNAME', 
            'MIDDLENAME', 'SUFFIX', 'CHECK-IN', 'SITE', 'PARTY'
        ]
        missing_recommended = [col for col in recommended_columns if col not in df.columns]

        if missing_recommended:
            self.log(f"INFO: Missing recommended columns: {', '.join(missing_recommended)}")
            self.log("These columns are optional but provide additional voter information.")

        # Check for VUID or CERT column (required for cross-referencing)
        has_vuid = 'VUID' in df.columns
        has_cert = 'CERT' in df.columns
        has_id = 'ID' in df.columns

        if not has_vuid and not has_cert:
            if has_id:
                self.log("INFO: VUID and CERT columns not found. Will attempt to use ID column as VUID.")
            else:
                self.log("WARNING: VUID, CERT, and ID columns not found. Cross-referencing will not be available.")
                result.add_warning(0, "VUID/CERT columns missing - cross-referencing disabled")
        elif not has_vuid and has_cert:
            self.log("INFO: VUID column not found. Using CERT column as VUID for cross-referencing.")

        # Validate each row
        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 for header and 0-indexing

            # Check for empty address
            if pd.isna(row['ADDRESS']) or str(row['ADDRESS']).strip() == '':
                result.add_error(row_num, "Empty address")
                continue

            # Check for malformed address (very basic check)
            address = str(row['ADDRESS']).strip()
            if len(address) < 5:
                result.add_error(row_num, "Address too short")
                continue

            # Check for suspicious patterns
            if address.upper().startswith('PO BOX'):
                result.add_warning(row_num, "PO Box address")

            result.valid_count += 1

        return result

    
    def clean_addresses(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize addresses with improved formatting for better geocoding."""
        def clean_address(address):
            if pd.isna(address):
                return None
            
            # Convert to string and uppercase
            address = str(address).upper().strip()
            
            # Remove extra whitespace
            address = ' '.join(address.split())
            
            # Standardize abbreviations
            replacements = {
                r'\bST\b': 'STREET',
                r'\bAVE\b': 'AVENUE',
                r'\bRD\b': 'ROAD',
                r'\bDR\b': 'DRIVE',
                r'\bLN\b': 'LANE',
                r'\bCT\b': 'COURT',
                r'\bAPT\b': 'APARTMENT',
                r'\bN\b': 'NORTH',
                r'\bS\b': 'SOUTH',
                r'\bE\b': 'EAST',
                r'\bW\b': 'WEST',
                r'\bBLVD\b': 'BOULEVARD',
                r'\bCIR\b': 'CIRCLE',
            }
            
            for pattern, replacement in replacements.items():
                address = re.sub(pattern, replacement, address)
            
            # Extract ZIP code if present
            zip_match = re.search(r'\b(\d{5})\b', address)
            zip_code = zip_match.group(1) if zip_match else None
            
            # Check if address already has city name
            has_city = any(city in address for city in [
                'MCALLEN', 'EDINBURG', 'MISSION', 'PHARR', 'WESLACO',
                'BROWNSVILLE', 'HARLINGEN', 'SAN BENITO', 'DONNA', 'ALAMO',
                'MERCEDES', 'LA JOYA', 'ELSA', 'EDCOUCH', 'SAN JUAN'
            ])
            
            # If no city but has county info, add default city based on county
            if not has_city:
                # Use county to determine likely city
                if hasattr(self, 'county'):
                    if self.county.upper() == 'HIDALGO':
                        # For Hidalgo County, default to McAllen (largest city)
                        if zip_code:
                            address = f"{address.replace(zip_code, '').strip()}, MCALLEN, TEXAS {zip_code}"
                        else:
                            address = f"{address}, MCALLEN, TEXAS"
                    elif self.county.upper() == 'CAMERON':
                        # For Cameron County, default to Brownsville
                        if zip_code:
                            address = f"{address.replace(zip_code, '').strip()}, BROWNSVILLE, TEXAS {zip_code}"
                        else:
                            address = f"{address}, BROWNSVILLE, TEXAS"
                    else:
                        # Generic Texas address
                        if zip_code:
                            address = f"{address.replace(zip_code, '').strip()}, TEXAS {zip_code}"
                        else:
                            address = f"{address}, TEXAS"
                else:
                    # No county info, just add Texas
                    if 'TX' not in address and 'TEXAS' not in address:
                        address = f"{address}, TEXAS"
            else:
                # Has city, just ensure TEXAS is present (use TEXAS not TX for cache consistency)
                if 'TX' not in address and 'TEXAS' not in address:
                    if zip_code:
                        address = f"{address.replace(zip_code, '').strip()}, TEXAS {zip_code}"
                    else:
                        address = f"{address}, TEXAS"
                elif ' TX ' in address or address.endswith(' TX'):
                    # Replace TX with TEXAS for cache consistency
                    address = address.replace(' TX ', ' TEXAS ').replace(' TX', ' TEXAS')
            
            return address
        
        df['cleaned_address'] = df['ADDRESS'].apply(clean_address)
        df = df.dropna(subset=['cleaned_address'])
        
        return df
    
    def geocode_addresses(self, df: pd.DataFrame) -> pd.DataFrame:
        """Geocode addresses using parallel processing for configurable speed."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        # STEP 1: Check cache first to see how many addresses are already geocoded
        self.log("Checking cache for previously geocoded addresses...")
        cache_hits = 0
        cache_misses = 0
        
        for idx, row in df.iterrows():
            address = row['cleaned_address']
            cached = self.geocoder.cache.get(address)
            if cached:
                cache_hits += 1
            else:
                cache_misses += 1
        
        # Log the cache analysis
        total_addresses = len(df)
        cache_hit_rate = (cache_hits / total_addresses * 100) if total_addresses > 0 else 0
        
        self.log(f"Cache analysis complete:")
        self.log(f"  Total addresses: {total_addresses:,}")
        self.log(f"  Already geocoded (cache hits): {cache_hits:,} ({cache_hit_rate:.1f}%)")
        self.log(f"  Need geocoding (cache misses): {cache_misses:,} ({100-cache_hit_rate:.1f}%)")
        self.log("")
        
        # STEP 2: Process addresses in two phases - cached first, then new
        results = []
        results_lock = threading.Lock()
        
        # Use configured number of parallel workers
        max_workers = self.max_workers
        
        # Phase 1: Process all cached addresses first (instant)
        self.log("Phase 1: Processing cached addresses...")
        cached_addresses = []
        uncached_addresses = []
        
        for idx, row in df.iterrows():
            address = row['cleaned_address']
            cached = self.geocoder.cache.get(address)
            if cached:
                cached_addresses.append((idx, row, cached))
            else:
                uncached_addresses.append((idx, row))
        
        # Process cached addresses instantly
        for idx, row, cached_result in cached_addresses:
            address = row['cleaned_address']
            
            record = {
                'address': address,
                'original_address': row['ADDRESS'],
                'lat': cached_result['lat'],
                'lng': cached_result['lng'],
                'display_name': cached_result['display_name'],
                'precinct': row['PRECINCT'],
                'ballot_style': row['BALLOT STYLE']
            }
            
            # Include all standard voter data columns if available
            optional_columns = [
                'ID', 'VUID', 'CERT', 'LASTNAME', 'FIRSTNAME', 
                'MIDDLENAME', 'SUFFIX', 'CHECK-IN', 'SITE', 'PARTY'
            ]
            
            for col in optional_columns:
                if col in row and pd.notna(row[col]):
                    json_key = col.lower().replace('-', '_')
                    record[json_key] = str(row[col])
            
            # Handle VUID fallback logic
            if 'vuid' not in record and 'cert' in record:
                cert_value = str(record['cert'])
                if cert_value and cert_value != 'nan':
                    record['vuid'] = cert_value
            
            if 'vuid' not in record and 'id' in record:
                id_value = str(record['id'])
                if id_value.isdigit() and len(id_value) == 10:
                    record['vuid'] = id_value
            
            # Build full name
            name_parts = []
            if 'FIRSTNAME' in row and pd.notna(row['FIRSTNAME']):
                name_parts.append(str(row['FIRSTNAME']))
            if 'MIDDLENAME' in row and pd.notna(row['MIDDLENAME']):
                name_parts.append(str(row['MIDDLENAME']))
            if 'LASTNAME' in row and pd.notna(row['LASTNAME']):
                name_parts.append(str(row['LASTNAME']))
            if 'SUFFIX' in row and pd.notna(row['SUFFIX']):
                name_parts.append(str(row['SUFFIX']))
            
            if name_parts:
                record['name'] = ' '.join(name_parts)
            
            results.append(record)
            self.geocoded_count += 1
            self.cache_hits += 1  # Track cache hits
            self.processed_records += 1
            self.progress = 0.2 + (0.5 * (self.processed_records / self.total_records))
        
        self.log(f"Phase 1 complete: {len(cached_addresses):,} cached addresses processed instantly")
        
        # Phase 2: Geocode uncached addresses with parallel processing
        if uncached_addresses:
            self.log(f"Phase 2: Geocoding {len(uncached_addresses):,} new addresses with {max_workers} workers...")
            
            def geocode_single_address(idx_row):
                """Geocode a single address (runs in parallel)."""
                idx, row = idx_row
                address = row['cleaned_address']
                
                # Geocode
                result = self.geocoder.geocode(address)
                
                if result:
                    record = {
                        'address': address,
                        'original_address': row['ADDRESS'],
                        'lat': result['lat'],
                        'lng': result['lng'],
                        'display_name': result['display_name'],
                        'precinct': row['PRECINCT'],
                        'ballot_style': row['BALLOT STYLE']
                    }
                    
                    # Include all standard voter data columns if available
                    optional_columns = [
                        'ID', 'VUID', 'CERT', 'LASTNAME', 'FIRSTNAME', 
                        'MIDDLENAME', 'SUFFIX', 'CHECK-IN', 'SITE', 'PARTY'
                    ]
                    
                    for col in optional_columns:
                        if col in row and pd.notna(row[col]):
                            # Convert column name to lowercase with underscores for JSON
                            json_key = col.lower().replace('-', '_')
                            record[json_key] = str(row[col])
                    
                    # Handle VUID fallback logic
                    # Priority 1: Use CERT column as VUID if VUID is missing
                    if 'vuid' not in record and 'cert' in record:
                        cert_value = str(record['cert'])
                        # CERT is the primary VUID identifier
                        if cert_value and cert_value != 'nan':
                            record['vuid'] = cert_value
                    
                    # Priority 2: If VUID still missing, check if ID looks like a VUID (10 digits)
                    if 'vuid' not in record and 'id' in record:
                        id_value = str(record['id'])
                        # Check if ID is 10 digits (VUID format)
                        if id_value.isdigit() and len(id_value) == 10:
                            record['vuid'] = id_value
                    
                    # Build full name if name components are available
                    name_parts = []
                    if 'FIRSTNAME' in row and pd.notna(row['FIRSTNAME']):
                        name_parts.append(str(row['FIRSTNAME']))
                    if 'MIDDLENAME' in row and pd.notna(row['MIDDLENAME']):
                        name_parts.append(str(row['MIDDLENAME']))
                    if 'LASTNAME' in row and pd.notna(row['LASTNAME']):
                        name_parts.append(str(row['LASTNAME']))
                    if 'SUFFIX' in row and pd.notna(row['SUFFIX']):
                        name_parts.append(str(row['SUFFIX']))
                    
                    if name_parts:
                        record['name'] = ' '.join(name_parts)
                    
                    with results_lock:
                        self.geocoded_count += 1
                    
                    return ('success', record)
                else:
                    error_record = {
                        'address': address,
                        'error': 'Geocoding failed'
                    }
                    # Try to include VUID for error tracking
                    if 'VUID' in row and pd.notna(row['VUID']):
                        error_record['vuid'] = str(row['VUID'])
                    elif 'CERT' in row and pd.notna(row['CERT']):
                        error_record['vuid'] = str(row['CERT'])
                    elif 'ID' in row and pd.notna(row['ID']):
                        id_value = str(row['ID'])
                        if id_value.isdigit() and len(id_value) == 10:
                            error_record['vuid'] = id_value
                    
                    with results_lock:
                        self.failed_count += 1
                    
                    return ('error', error_record)
            
            # Process addresses in parallel
            self.log(f"Starting parallel geocoding with {max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all geocoding tasks
                future_to_idx = {executor.submit(geocode_single_address, idx_row): idx_row 
                               for idx_row in uncached_addresses}
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_idx):
                    try:
                        status, record = future.result()
                        
                        if status == 'success':
                            results.append(record)
                        else:
                            self.errors.append(record)
                        
                        # Update progress
                        with results_lock:
                            self.processed_records += 1
                            self.progress = 0.2 + (0.5 * (self.processed_records / self.total_records))
                        
                        # Log progress every 100 records with visual bar
                        if self.processed_records % 100 == 0:
                            # Get current stats
                            stats = self.geocoder.get_stats()
                            cached = stats['cache_hits']
                            new_geocoded = self.geocoded_count - cached
                            
                            # Calculate percentages
                            cached_pct = (cached / self.processed_records * 100) if self.processed_records > 0 else 0
                            new_pct = (new_geocoded / self.processed_records * 100) if self.processed_records > 0 else 0
                            
                            # Create visual progress bar (50 chars wide)
                            bar_width = 50
                            cached_bars = int((cached / self.total_records) * bar_width)
                            new_bars = int((new_geocoded / self.total_records) * bar_width)
                            remaining_bars = bar_width - cached_bars - new_bars
                            
                            progress_bar = f"[{'#' * cached_bars}{'=' * new_bars}{'.' * remaining_bars}]"
                            
                            self.log(f"Progress: {self.processed_records}/{self.total_records} {progress_bar}")
                            self.log(f"  [CACHE] {cached:,} ({cached_pct:.1f}%) | [NEW] {new_geocoded:,} ({new_pct:.1f}%) | [FAIL] {self.failed_count}")
                            
                    except Exception as e:
                        self.log(f"Error processing address: {e}")
                        with results_lock:
                            self.failed_count += 1
                            self.processed_records += 1
            
            self.log(f"Parallel geocoding complete. Success: {self.geocoded_count}, Failed: {self.failed_count}")
        
        # Add visual summary
        stats = self.geocoder.get_stats()
        cached = stats['cache_hits']
        new_geocoded = self.geocoded_count - cached if self.geocoded_count > cached else 0
        
        self.log("")
        self.log("=" * 70)
        self.log("GEOCODING SUMMARY")
        self.log("=" * 70)
        self.log(f"Total addresses processed: {self.total_records:,}")
        self.log(f"  [CACHE] From cache (previously geocoded): {cached:,} ({cached/self.total_records*100:.1f}%)")
        self.log(f"  [NEW] Newly geocoded: {new_geocoded:,} ({new_geocoded/self.total_records*100:.1f}%)")
        self.log(f"  [FAIL] Failed: {self.failed_count:,} ({self.failed_count/self.total_records*100:.1f}%)")
        self.log("=" * 70)
        self.log("")
        
        return pd.DataFrame(results)
    
    def generate_outputs(self, df: pd.DataFrame):
        """Generate JSON output files."""
        # Ensure data directory exists
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Calculate household voter counts by grouping by coordinates
        household_counts = df.groupby(['lat', 'lng']).size().to_dict()

        # Cross-reference voters against earlier datasets for party switching detection
        engine = CrossReferenceEngine(self.county, self.election_date or '', Config.DATA_DIR)
        previous_parties = engine.cross_reference(df)

        # Generate map_data.json
        map_data = {
            'type': 'FeatureCollection',
            'features': []
        }

        for idx, row in df.iterrows():
            # Calculate party affiliation fields
            party_affiliation_current = self._extract_current_party(row)
            party_history = self._extract_party_history(row)
            has_switched_parties = self._detect_party_switching(party_history)
            election_dates_participated = self._extract_election_dates(row)
            voted_in_current_election = self._check_voted_in_current(row)
            is_registered = self._check_registration_status(row)

            # Get household count
            coord_key = (row['lat'], row['lng'])
            household_voter_count = household_counts.get(coord_key, 1)

            properties = {
                'address': row['display_name'],
                'original_address': row['original_address'],
                'precinct': row['precinct'],
                'ballot_style': row['ballot_style'],

                # Party affiliation fields
                'party_affiliation_current': party_affiliation_current,
                'party_affiliation_previous': previous_parties.get(idx, ''),
                'party_history': party_history,
                'has_switched_parties': has_switched_parties,
                'election_dates_participated': election_dates_participated,
                'voted_in_current_election': voted_in_current_election,
                'is_registered': is_registered,
                'household_voter_count': household_voter_count
            }

            # Include all optional voter data fields if available
            optional_fields = [
                'id', 'vuid', 'cert', 'lastname', 'firstname', 
                'middlename', 'suffix', 'check_in', 'site', 'party', 'name'
            ]
            
            for field in optional_fields:
                if field in row and pd.notna(row[field]):
                    properties[field] = row[field]

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [row['lng'], row['lat']]
                },
                'properties': properties
            }
            map_data['features'].append(feature)

        # Create metadata-aware filename
        # Format: map_data_{county}_{year}_{election_type}_{party}_{date}.json
        # Example: map_data_Hidalgo_2022_primary_democratic_20220301.json
        date_str = self.election_date.replace('-', '') if self.election_date else 'unknown'
        party_suffix = f'_{self.primary_party}' if self.primary_party else ''
        map_data_filename = f'map_data_{self.county}_{self.year}_{self.election_type}{party_suffix}_{date_str}.json'
        map_data_path = Config.DATA_DIR / map_data_filename
        with open(map_data_path, 'w') as f:
            json.dump(map_data, f, indent=2)

        # Also save as default map_data.json for backward compatibility
        default_map_data_path = Config.DATA_DIR / 'map_data.json'
        with open(default_map_data_path, 'w') as f:
            json.dump(map_data, f, indent=2)

        # Generate metadata.json
        stats = self.geocoder.get_stats()
        metadata = {
            'year': self.year,
            'county': self.county,
            'election_type': self.election_type,
            'election_date': self.election_date,
            'voting_method': self.voting_method,
            'primary_party': self.primary_party,  # Include party for primaries
            'original_filename': self.original_filename,
            'last_updated': datetime.now().isoformat(),
            'total_addresses': self.total_records,
            'successfully_geocoded': self.geocoded_count,
            'failed_addresses': self.failed_count,
            'cache_hits': stats['cache_hits'],
            'cache_hit_rate': stats['cache_hit_rate'],
            'api_calls': stats['api_calls']
        }

        # Save metadata with same naming pattern (include party for primaries)
        party_suffix = f'_{self.primary_party}' if self.primary_party else ''
        metadata_filename = f'metadata_{self.county}_{self.year}_{self.election_type}{party_suffix}_{date_str}.json'
        metadata_path = Config.DATA_DIR / metadata_filename
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Also save as default metadata.json for backward compatibility
        default_metadata_path = Config.DATA_DIR / 'metadata.json'
        with open(default_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Generate error CSV if there are errors
        if self.errors:
            error_csv_path = Config.DATA_DIR / 'processing_errors.csv'
            error_df = pd.DataFrame(self.errors)
            error_df.to_csv(error_csv_path, index=False)
        
        # Re-resolve unmatched VUIDs in early vote GeoJSONs
        try:
            self.re_resolve_unmatched()
        except Exception as e:
            logger.warning(f"Re-resolution of unmatched VUIDs failed: {e}")

    
    def deploy_outputs(self):
            """Copy output files to public directory."""
            import shutil

            # Ensure public/data directory exists
            public_data_dir = Config.PUBLIC_DIR / 'data'
            public_data_dir.mkdir(parents=True, exist_ok=True)

            # Create filename pattern based on election metadata
            date_str = self.election_date.replace('-', '') if self.election_date else 'unknown'

            # Year-specific filenames (include party for primaries)
            party_suffix = f'_{self.primary_party}' if self.primary_party else ''
            map_data_filename = f'map_data_{self.county}_{self.year}_{self.election_type}{party_suffix}_{date_str}.json'
            metadata_filename = f'metadata_{self.county}_{self.year}_{self.election_type}{party_suffix}_{date_str}.json'

            # Copy year-specific files
            year_specific_files = [map_data_filename, metadata_filename]

            for filename in year_specific_files:
                src = Config.DATA_DIR / filename
                dst = public_data_dir / filename

                if src.exists():
                    shutil.copy2(src, dst)
                    self.log(f"Deployed {filename}")
                else:
                    self.log(f"Warning: {filename} not found in data directory")

            # Copy backward-compatible default files (map_data.json, metadata.json)
            default_files = ['map_data.json', 'metadata.json']

            for filename in default_files:
                src = Config.DATA_DIR / filename
                dst = public_data_dir / filename

                if src.exists():
                    shutil.copy2(src, dst)
                    self.log(f"Deployed {filename} (backward compatibility)")
                else:
                    self.log(f"Warning: {filename} not found in data directory")


    # ============================================================================
    # PARTY AFFILIATION HELPER METHODS
    # ============================================================================
    
    def _extract_current_party(self, row) -> str:
        """Extract current party affiliation from voter data."""
        # PRIORITY 1: Check for PARTY column (from CSV upload)
        if 'party' in row and pd.notna(row['party']):
            party_code = str(row['party']).strip().upper()
            # Map single-letter codes to full party names
            if party_code == 'D':
                return 'Democratic'
            elif party_code == 'R':
                return 'Republican'
            elif party_code in ['DEM', 'DEMOCRAT', 'DEMOCRATIC']:
                return 'Democratic'
            elif party_code in ['REP', 'REPUBLICAN']:
                return 'Republican'
            else:
                # Return the raw value if it doesn't match known codes
                return party_code
        
        # PRIORITY 2: Check for primary_party from upload form (for primary elections)
        if hasattr(self, 'primary_party') and self.primary_party:
            if self.primary_party.lower() == 'democratic':
                return 'Democratic'
            elif self.primary_party.lower() == 'republican':
                return 'Republican'
        
        # PRIORITY 3: Check for party_affiliation column (from VUID system)
        if 'party_affiliation' in row and pd.notna(row['party_affiliation']):
            return str(row['party_affiliation'])
        
        # PRIORITY 4: Check ballot_style for party indicators
        if 'ballot_style' in row and pd.notna(row['ballot_style']):
            ballot = str(row['ballot_style']).upper()
            if 'REP' in ballot or 'REPUBLICAN' in ballot:
                return 'Republican'
            elif 'DEM' in ballot or 'DEMOCRAT' in ballot:
                return 'Democratic'
        
        # PRIORITY 5: Check for primary election type
        if hasattr(self, 'election_type') and self.election_type:
            if 'republican' in self.election_type.lower():
                return 'Republican'
            elif 'democrat' in self.election_type.lower():
                return 'Democratic'
        
        return ''
    
    def _extract_party_history(self, row) -> list:
        """Extract party history from voter data."""
        history = []
        
        # If there's a party_history column (from VUID system)
        if 'party_history' in row and pd.notna(row['party_history']):
            try:
                if isinstance(row['party_history'], str):
                    import json
                    history = json.loads(row['party_history'])
                elif isinstance(row['party_history'], list):
                    history = row['party_history']
            except:
                pass
        
        # Add current party to history if not empty
        current_party = self._extract_current_party(row)
        if current_party and current_party not in history:
            history.append(current_party)
        
        return history
    
    def _detect_party_switching(self, party_history: list) -> bool:
        """Detect if voter has switched parties based on history."""
        if not party_history or len(party_history) < 2:
            return False
        
        # Check if history contains both Republican and Democratic
        has_republican = any('republican' in str(p).lower() or 'rep' in str(p).lower() 
                            for p in party_history)
        has_democratic = any('democrat' in str(p).lower() or 'dem' in str(p).lower() 
                            for p in party_history)
        
        return has_republican and has_democratic
    
    def _extract_election_dates(self, row) -> list:
        """Extract election dates participated from voter data."""
        dates = []
        
        # Check for election_dates column
        if 'election_dates' in row and pd.notna(row['election_dates']):
            try:
                if isinstance(row['election_dates'], str):
                    import json
                    dates = json.loads(row['election_dates'])
                elif isinstance(row['election_dates'], list):
                    dates = row['election_dates']
            except:
                pass
        
        # Add current election date if not in list
        if hasattr(self, 'election_date') and self.election_date:
            if self.election_date not in dates:
                dates.append(self.election_date)
        
        return dates
    
    def _check_voted_in_current(self, row) -> bool:
        """Check if voter voted in current election."""
        # Check for explicit voted column
        if 'voted' in row and pd.notna(row['voted']):
            return bool(row['voted'])
        
        # Check for vote_method column (if present, they voted)
        if 'vote_method' in row and pd.notna(row['vote_method']):
            return True
        
        # Check for vote_date column
        if 'vote_date' in row and pd.notna(row['vote_date']):
            return True
        
        # Default to False if no voting indicators
        return False
    
    def _check_registration_status(self, row) -> bool:
        """Check if voter is registered."""
        # Check for registration_status column
        if 'registration_status' in row and pd.notna(row['registration_status']):
            status = str(row['registration_status']).lower()
            return status in ['active', 'registered']
        
        # Check for status column
        if 'status' in row and pd.notna(row['status']):
            status = str(row['status']).lower()
            return status in ['active', 'registered']
        
        # If we have a VUID, assume registered
        if 'vuid' in row and pd.notna(row['vuid']):
            return True
        
        # Default to True (assume registered if in voter roll)
        return True

    # ================================================================
    # EARLY VOTE ROSTER PROCESSING
    # ================================================================

    @staticmethod
    def detect_early_vote_roster(df: pd.DataFrame) -> bool:
        """Detect if a DataFrame is an early vote roster (has VUID but no ADDRESS)."""
        return has_vuid_column(df) and not has_address_column(df)

    def process_early_vote_roster(self, df: pd.DataFrame):
        """Process an early vote roster through the VUID resolution pipeline.
        
        This replaces the standard geocoding pipeline for files that have
        VUID but no address column.
        """
        self.log("Early vote roster detected — using VUID resolution pipeline")
        
        # Normalize column names
        df = normalize_column_names(df)
        
        # Validate VUID column exists after normalization
        if 'vuid' not in df.columns:
            raise ValueError("VUID column is required for Early Vote Roster processing")
        
        # Drop rows with empty VUID
        df = df.dropna(subset=['vuid'])
        df = df[df['vuid'].astype(str).str.strip() != '']
        
        if len(df) == 0:
            raise ValueError("File is empty or malformed")
        
        self.total_records = len(df)
        self.log(f"Processing {self.total_records} early vote records")
        
        # Parse voter names
        if 'voter_name' in df.columns:
            names = df['voter_name'].apply(parse_voter_name)
            df['lastname'] = names.apply(lambda x: x[0])
            df['firstname'] = names.apply(lambda x: x[1])
        else:
            df['lastname'] = ''
            df['firstname'] = ''
        
        # Build VUID lookup from existing datasets
        resolver = VUIDResolver(self.county, Config.DATA_DIR)
        lookup_count = resolver.build_lookup()
        self.log(f"VUID lookup built with {lookup_count} known VUIDs")
        
        # Resolve each VUID
        matched = 0
        unmatched = 0
        
        # Extract roster date from the filename timestamp (e.g. _202602221003529256 → 2026-02-22)
        # This is the date the file was generated, NOT the election date
        roster_date = self._extract_roster_date_from_filename()
        self.log(f"Roster date from filename: {roster_date}")
        primary_party = self.primary_party or ''
        
        # Prepare output columns
        results = []
        for idx, row in df.iterrows():
            raw_vuid = row.get('vuid', '')
            normalized_vuid = VUIDResolver.normalize_vuid(raw_vuid)
            
            match = resolver.resolve(normalized_vuid)
            
            record = {
                'vuid': normalized_vuid,
                'lastname': row.get('lastname', ''),
                'firstname': row.get('firstname', ''),
                'precinct': str(row.get('precinct', '')).strip(),
                'early_vote_day': roster_date,
                'voted_in_current_election': True,
                'is_registered': True,
            }
            
            if match:
                record['lat'] = match['lat']
                record['lng'] = match['lng']
                record['address'] = match['address']
                record['display_name'] = match['display_name']
                record['unmatched'] = False
                
                # Set party affiliation
                existing_party = match.get('party_affiliation_current', '')
                if primary_party:
                    record['party_affiliation_current'] = primary_party.capitalize()
                    if existing_party and existing_party.lower() != primary_party.lower():
                        record['party_affiliation_previous'] = existing_party
                        record['has_switched_parties'] = True
                    else:
                        record['party_affiliation_previous'] = ''
                        record['has_switched_parties'] = False
                else:
                    record['party_affiliation_current'] = existing_party
                    record['party_affiliation_previous'] = ''
                    record['has_switched_parties'] = False
                
                matched += 1
            else:
                record['lat'] = None
                record['lng'] = None
                record['address'] = ''
                record['display_name'] = ''
                record['unmatched'] = True
                record['party_affiliation_current'] = primary_party.capitalize() if primary_party else ''
                record['party_affiliation_previous'] = ''
                record['has_switched_parties'] = False
                unmatched += 1
            
            results.append(record)
            self.processed_records += 1
            self.progress = 0.2 + (0.6 * (self.processed_records / self.total_records))
        
        self.log(f"VUID resolution: {matched} matched, {unmatched} unmatched")
        self.geocoded_count = matched
        self.failed_count = unmatched
        
        result_df = pd.DataFrame(results)
        
        # Generate outputs
        self.generate_early_vote_outputs(result_df, matched, unmatched, roster_date)
        
        self.progress = 1.0
        self.status = 'completed'
        self.completed_at = datetime.now()
        processing_time = (self.completed_at - self.started_at).total_seconds()
        self.log(f"Early vote processing completed in {processing_time:.1f}s")

    def _extract_roster_date_from_filename(self) -> str:
        """Extract the roster date from the original filename's timestamp suffix.
        
        Filenames like 'EV DEM Roster March 3, 2026 (Cumulative)_202602221003529256'
        have a timestamp suffix where the first 8 digits are YYYYMMDD — the date
        the file was generated/updated, which is the roster date.
        
        Falls back to today's date if no timestamp is found.
        """
        import re
        filename = self.original_filename or ''
        # Remove extension
        name = re.sub(r'\.(csv|CSV)$', '', filename)
        
        # Look for timestamp suffix: underscore followed by 14-20 digits at end
        match = re.search(r'_(\d{14,20})$', name)
        if match:
            ts = match.group(1)
            try:
                # First 8 digits = YYYYMMDD
                return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
            except (IndexError, ValueError):
                pass
        
        # Fallback: try to find any 8-digit date-like sequence at the end
        match = re.search(r'_(\d{8})$', name)
        if match:
            ds = match.group(1)
            try:
                datetime.strptime(ds, '%Y%m%d')
                return f"{ds[0:4]}-{ds[4:6]}-{ds[6:8]}"
            except ValueError:
                pass
        
        # Last resort: today's date
        self.log("Warning: Could not extract roster date from filename, using today's date")
        return datetime.now().strftime('%Y-%m-%d')

    def generate_early_vote_outputs(self, df: pd.DataFrame, matched: int, unmatched: int, roster_date: str):
        """Generate GeoJSON day snapshot and cumulative files for early vote data."""
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Build GeoJSON features
        features = []
        for _, row in df.iterrows():
            if row.get('unmatched') or row.get('lat') is None:
                geometry = None
            else:
                geometry = {
                    'type': 'Point',
                    'coordinates': [row['lng'], row['lat']]
                }
            
            props = {
                'vuid': row.get('vuid', ''),
                'lastname': row.get('lastname', ''),
                'firstname': row.get('firstname', ''),
                'precinct': row.get('precinct', ''),
                'address': row.get('address', ''),
                'display_name': row.get('display_name', ''),
                'original_address': '',
                'party_affiliation_current': row.get('party_affiliation_current', ''),
                'party_affiliation_previous': row.get('party_affiliation_previous', ''),
                'early_vote_day': row.get('early_vote_day', ''),
                'unmatched': bool(row.get('unmatched', False)),
                'ballot_style': '',
                'household_voter_count': 1,
                'has_switched_parties': bool(row.get('has_switched_parties', False)),
                'voted_in_current_election': True,
                'is_registered': True,
            }
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': props,
            })
        
        map_data = {'type': 'FeatureCollection', 'features': features}
        
        # Day snapshot filename
        date_str = roster_date.replace('-', '')
        party_suffix = f'_{self.primary_party}' if self.primary_party else ''
        snapshot_filename = f'map_data_{self.county}_{self.year}_{self.election_type}{party_suffix}_{date_str}.json'
        snapshot_path = Config.DATA_DIR / snapshot_filename
        
        with open(snapshot_path, 'w') as f:
            json.dump(map_data, f, indent=2)
        self.log(f"Day snapshot saved: {snapshot_filename}")
        
        # Day metadata
        metadata = {
            'year': self.year,
            'county': self.county,
            'election_type': self.election_type,
            'election_date': roster_date,
            'voting_method': self.voting_method or 'early-voting',
            'primary_party': self.primary_party,
            'early_vote_day': roster_date,
            'is_early_voting': True,
            'is_cumulative': False,
            'original_filename': self.original_filename,
            'last_updated': datetime.now().isoformat(),
            'total_addresses': len(df),
            'matched_vuids': matched,
            'unmatched_vuids': unmatched,
            'successfully_geocoded': 0,
            'failed_addresses': 0,
        }
        
        meta_filename = f'metadata_{self.county}_{self.year}_{self.election_type}{party_suffix}_{date_str}.json'
        meta_path = Config.DATA_DIR / meta_filename
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Generate cumulative file
        self._generate_cumulative(party_suffix)
        
        # Deploy early vote files to public directory
        self._deploy_early_vote_outputs(snapshot_filename, meta_filename, party_suffix)

    def _deploy_early_vote_outputs(self, snapshot_filename: str, meta_filename: str, party_suffix: str):
        """Deploy early vote snapshot, metadata, and cumulative files to public directory."""
        import shutil
        
        public_data_dir = Config.PUBLIC_DIR / 'data'
        public_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Deploy day snapshot + metadata
        for filename in [snapshot_filename, meta_filename]:
            src = Config.DATA_DIR / filename
            dst = public_data_dir / filename
            if src.exists():
                shutil.copy2(src, dst)
                self.log(f"Deployed {filename}")
            else:
                self.log(f"Warning: {filename} not found in data directory")
        
        # Deploy cumulative files
        cum_map = f'map_data_{self.county}_{self.year}_{self.election_type}{party_suffix}_cumulative.json'
        cum_meta = f'metadata_{self.county}_{self.year}_{self.election_type}{party_suffix}_cumulative.json'
        
        for filename in [cum_map, cum_meta]:
            src = Config.DATA_DIR / filename
            dst = public_data_dir / filename
            if src.exists():
                shutil.copy2(src, dst)
                self.log(f"Deployed {filename}")
            else:
                self.log(f"Warning: {filename} not found in data directory")

    def _generate_cumulative(self, party_suffix: str):
        """Merge all day snapshots for same county/election/party into cumulative file."""
        pattern = f'map_data_{self.county}_{self.year}_{self.election_type}{party_suffix}_*.json'
        snapshot_files = sorted(Config.DATA_DIR.glob(pattern))
        
        # Exclude cumulative file itself
        snapshot_files = [f for f in snapshot_files if 'cumulative' not in f.name]
        
        if not snapshot_files:
            return
        
        # Merge all features, deduplicate by VUID (keep most recent)
        all_features = {}
        day_snapshots = []
        
        for filepath in snapshot_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Extract date from filename
                date_part = filepath.stem.split('_')[-1]
                day_snapshots.append(date_part)
                
                for feature in data.get('features', []):
                    vuid = feature.get('properties', {}).get('vuid', '')
                    if vuid:
                        normalized = VUIDResolver.normalize_vuid(vuid)
                        all_features[normalized] = feature
            except Exception as e:
                logger.warning(f"Error reading snapshot {filepath}: {e}")
        
        features_list = list(all_features.values())
        cumulative_data = {'type': 'FeatureCollection', 'features': features_list}
        
        # Save cumulative file
        cum_filename = f'map_data_{self.county}_{self.year}_{self.election_type}{party_suffix}_cumulative.json'
        cum_path = Config.DATA_DIR / cum_filename
        with open(cum_path, 'w') as f:
            json.dump(cumulative_data, f, indent=2)
        
        # Count matched/unmatched
        cum_matched = sum(1 for f in features_list if not f.get('properties', {}).get('unmatched', False))
        cum_unmatched = sum(1 for f in features_list if f.get('properties', {}).get('unmatched', False))
        
        # Cumulative metadata
        cum_meta = {
            'year': self.year,
            'county': self.county,
            'election_type': self.election_type,
            'primary_party': self.primary_party,
            'is_early_voting': True,
            'is_cumulative': True,
            'last_updated': datetime.now().isoformat(),
            'total_addresses': len(features_list),
            'matched_vuids': cum_matched,
            'unmatched_vuids': cum_unmatched,
            'day_snapshots': sorted(day_snapshots),
        }
        
        cum_meta_filename = f'metadata_{self.county}_{self.year}_{self.election_type}{party_suffix}_cumulative.json'
        cum_meta_path = Config.DATA_DIR / cum_meta_filename
        with open(cum_meta_path, 'w') as f:
            json.dump(cum_meta, f, indent=2)
        
        self.log(f"Cumulative file updated: {len(features_list)} total voters ({cum_matched} matched, {cum_unmatched} unmatched)")

    def re_resolve_unmatched(self):
        """After a full voter file is processed, re-resolve unmatched VUIDs in early vote GeoJSONs."""
        # Build lookup from the newly processed data
        resolver = VUIDResolver(self.county, Config.DATA_DIR)
        resolver.build_lookup()
        
        if not resolver.vuid_lookup:
            return
        
        # Find early vote GeoJSON files for this county
        pattern = f'map_data_{self.county}_*_cumulative.json'
        cum_files = list(Config.DATA_DIR.glob(pattern))
        
        # Also check individual day snapshots
        pattern_all = f'map_data_{self.county}_*.json'
        all_files = [f for f in Config.DATA_DIR.glob(pattern_all) if 'cumulative' not in f.name]
        
        files_to_check = cum_files + all_files
        
        for filepath in files_to_check:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                features = data.get('features', [])
                updated = 0
                
                for feature in features:
                    props = feature.get('properties', {})
                    if not props.get('unmatched', False):
                        continue
                    
                    vuid = props.get('vuid', '')
                    if not vuid:
                        continue
                    
                    match = resolver.resolve(vuid)
                    if match and match.get('lat') is not None:
                        feature['geometry'] = {
                            'type': 'Point',
                            'coordinates': [match['lng'], match['lat']]
                        }
                        props['address'] = match['address']
                        props['display_name'] = match['display_name']
                        props['unmatched'] = False
                        updated += 1
                
                if updated > 0:
                    with open(filepath, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    # Update corresponding metadata
                    meta_name = filepath.name.replace('map_data_', 'metadata_')
                    meta_path = Config.DATA_DIR / meta_name
                    if meta_path.exists():
                        with open(meta_path, 'r') as f:
                            meta = json.load(f)
                        matched_count = sum(1 for feat in features if not feat.get('properties', {}).get('unmatched', False))
                        unmatched_count = sum(1 for feat in features if feat.get('properties', {}).get('unmatched', False))
                        meta['matched_vuids'] = matched_count
                        meta['unmatched_vuids'] = unmatched_count
                        meta['last_updated'] = datetime.now().isoformat()
                        with open(meta_path, 'w') as f:
                            json.dump(meta, f, indent=2)
                    
                    # Deploy updated files to public directory
                    import shutil
                    public_data_dir = Config.PUBLIC_DIR / 'data'
                    if public_data_dir.exists():
                        dst = public_data_dir / filepath.name
                        shutil.copy2(filepath, dst)
                        if meta_path.exists():
                            shutil.copy2(meta_path, public_data_dir / meta_name)
                    
                    self.log(f"Re-resolved {updated} VUIDs in {filepath.name}")
                    
            except Exception as e:
                logger.warning(f"Error re-resolving {filepath}: {e}")
