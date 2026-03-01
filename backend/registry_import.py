"""Voter registration file import module.

Parses the Hidalgo County voter registration Excel file and imports
all voter records into the SQLite database. Optimized for low-memory
servers by processing one sheet at a time without pre-counting.

Format:
- Multi-sheet Excel file with report headers
- Columns: VUID (1), Name (5), Address (14), Zip (21), Birth Year (25),
  Reg Date (26), Sex (28), Party (30), Precinct (32)
- Name format: "LASTNAME, FIRSTNAME M" or "LASTNAME, FIRSTNAME"
"""
import re
import gc
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

import database as db

logger = logging.getLogger(__name__)


def parse_voter_name(name_str: str) -> dict:
    """Parse 'LASTNAME, FIRSTNAME M' into components."""
    if not name_str or not isinstance(name_str, str):
        return {'lastname': '', 'firstname': '', 'middlename': '', 'suffix': ''}
    
    name_str = name_str.strip()
    parts = name_str.split(',', 1)
    lastname = parts[0].strip()
    
    firstname = ''
    middlename = ''
    suffix = ''
    
    if len(parts) > 1:
        rest = parts[1].strip().split()
        if rest:
            firstname = rest[0]
        if len(rest) > 1:
            suffixes = {'JR', 'SR', 'II', 'III', 'IV', 'V'}
            if rest[-1].upper() in suffixes:
                suffix = rest[-1]
                middlename = ' '.join(rest[1:-1])
            else:
                middlename = ' '.join(rest[1:])
    
    return {
        'lastname': lastname,
        'firstname': firstname,
        'middlename': middlename,
        'suffix': suffix
    }


def parse_address(address_str: str) -> dict:
    """Parse address string into address and city components."""
    if not address_str or not isinstance(address_str, str):
        return {'address': '', 'city': ''}
    
    address_str = address_str.strip()
    
    cities = [
        'MCALLEN', 'EDINBURG', 'MISSION', 'PHARR', 'WESLACO', 'DONNA',
        'MERCEDES', 'SAN JUAN', 'ALAMO', 'ALTON', 'ELSA', 'EDCOUCH',
        'LA JOYA', 'PALMVIEW', 'PALMHURST', 'HIDALGO', 'PENITAS',
        'SULLIVAN CITY', 'LA VILLA', 'PROGRESO', 'PROGRESO LAKES',
        'MONTE ALTO', 'HARGILL', 'LINN', 'LOPEZVILLE', 'SCISSORS',
        'ABRAM', 'DOFFING', 'GRANJENO', 'HAVANA', 'LA BLANCA',
        'MIDWAY NORTH', 'MIDWAY SOUTH', 'NORTH ALAMO', 'OLIVAREZ',
        'RELAMPAGO', 'SOUTH ALAMO', 'WEST PHARR',
    ]
    cities.sort(key=len, reverse=True)
    
    upper = address_str.upper()
    for city in cities:
        if upper.endswith(' ' + city):
            addr_part = address_str[:len(address_str) - len(city)].strip()
            return {'address': addr_part, 'city': city.title()}
    
    parts = address_str.rsplit(' ', 1)
    if len(parts) == 2:
        return {'address': parts[0], 'city': parts[1].title()}
    
    return {'address': address_str, 'city': ''}


class RegistryImportJob:
    """Background job for importing a voter registration file into the database.
    
    Optimized for low-memory servers (< 1GB RAM):
    - Skips the pre-counting pass to avoid reading the file twice
    - Processes one sheet at a time, freeing memory between sheets
    - Uses batched DB inserts for efficiency
    """
    
    def __init__(self, filepath: str, county: str, job_id: str = None):
        import uuid
        self.filepath = filepath
        self.county = county
        self.job_id = job_id or str(uuid.uuid4())
        self.status = 'queued'
        self.progress = 0.0
        self.total_records = 0  # Will be estimated, not pre-counted
        self.processed_records = 0
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.log_messages = []
        self.started_at = None
        self.completed_at = None
        self.original_filename = Path(filepath).name
    
    def log(self, message: str):
        timestamp = datetime.now().isoformat()
        self.log_messages.append({'timestamp': timestamp, 'message': message})
        logger.info(f"[Registry {self.job_id[:8]}] {message}")
    
    def _process_sheet(self, sheet_name: str, sheet_idx: int, num_sheets: int):
        """Process a single sheet and insert records into DB. Frees memory after."""
        self.log(f"Reading sheet {sheet_idx + 1}/{num_sheets}: {sheet_name}")
        
        df = pd.read_excel(self.filepath, header=None, sheet_name=sheet_name)
        num_rows = len(df)
        self.log(f"Sheet {sheet_name}: {num_rows} rows loaded")
        
        batch = []
        batch_size = 500
        sheet_count = 0
        
        for _, row in df.iterrows():
            # Extract VUID from column 1
            raw_vuid = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ''
            raw_vuid = raw_vuid.strip().replace('.0', '')
            
            if not re.match(r'^\d{7,10}$', raw_vuid):
                continue
            
            vuid = raw_vuid.zfill(10)
            
            # Extract name (column 5)
            name_str = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ''
            name_parts = parse_voter_name(name_str)
            
            # Extract address (column 14) and zip (column 21)
            address_raw = str(row.iloc[14]) if pd.notna(row.iloc[14]) else ''
            addr_parts = parse_address(address_raw)
            zip_code = str(row.iloc[21]).strip().replace('.0', '') if pd.notna(row.iloc[21]) else ''
            
            full_address = address_raw.strip()
            if zip_code:
                full_address += f', TX {zip_code}'
            
            # Extract other fields
            birth_year = None
            if pd.notna(row.iloc[25]):
                try:
                    birth_year = int(float(str(row.iloc[25])))
                except (ValueError, TypeError):
                    pass
            
            reg_date = ''
            if pd.notna(row.iloc[26]):
                try:
                    rd = pd.to_datetime(row.iloc[26])
                    reg_date = rd.strftime('%Y-%m-%d')
                except Exception:
                    reg_date = str(row.iloc[26])
            
            sex = str(row.iloc[28]).strip() if pd.notna(row.iloc[28]) else ''
            party = str(row.iloc[30]).strip() if pd.notna(row.iloc[30]) else ''
            precinct = str(row.iloc[32]).strip().replace('.0', '') if pd.notna(row.iloc[32]) else ''
            
            record = {
                'vuid': vuid,
                'lastname': name_parts['lastname'],
                'firstname': name_parts['firstname'],
                'middlename': name_parts['middlename'],
                'suffix': name_parts['suffix'],
                'address': full_address,
                'city': addr_parts['city'],
                'zip': zip_code,
                'county': self.county,
                'birth_year': birth_year,
                'registration_date': reg_date,
                'sex': sex,
                'registered_party': party,
                'current_party': '',
                'precinct': precinct,
                'lat': None,
                'lng': None,
                'source': 'registry'
            }
            
            batch.append(record)
            sheet_count += 1
            self.processed_records += 1
            self.imported_count += 1
            
            if len(batch) >= batch_size:
                db.upsert_voters_batch(batch)
                batch = []
                # Update progress based on sheet position
                sheet_progress = sheet_idx / num_sheets
                next_sheet_progress = (sheet_idx + 1) / num_sheets
                self.progress = sheet_progress + (next_sheet_progress - sheet_progress) * 0.9
        
        # Flush remaining batch
        if batch:
            db.upsert_voters_batch(batch)
        
        self.log(f"Sheet {sheet_name} complete: {sheet_count:,} voters imported ({self.processed_records:,} total)")
        
        # Free memory
        del df
        gc.collect()
        
        return sheet_count
    
    def run(self):
        """Execute the registry import — one sheet at a time for low memory."""
        self.status = 'running'
        self.started_at = datetime.now()
        self.log("Voter registry import started")
        
        try:
            db.init_db()
            
            # Get sheet names only (lightweight — doesn't load data)
            self.log("Reading sheet names...")
            xls = pd.ExcelFile(self.filepath)
            sheet_names = list(xls.sheet_names)
            xls.close()
            del xls
            gc.collect()
            
            num_sheets = len(sheet_names)
            self.log(f"Found {num_sheets} sheets — processing one at a time")
            
            # Process each sheet individually
            for sheet_idx, sheet_name in enumerate(sheet_names):
                self._process_sheet(sheet_name, sheet_idx, num_sheets)
                self.progress = (sheet_idx + 1) / num_sheets * 0.9
            
            self.total_records = self.processed_records
            self.progress = 0.9
            
            # Run post-import pipeline (backfill coords, election history, party update)
            self.log("Starting post-import pipeline...")
            try:
                from post_import import run_pipeline
                pipeline_result = run_pipeline(self.county, log_fn=self.log)
                self.log(f"Post-import pipeline finished: {pipeline_result.get('elapsed_seconds', 0)}s")
            except Exception as e:
                self.log(f"Post-import pipeline error (non-fatal): {e}")
                logger.exception(f"Post-import pipeline failed for {self.county}")
            
            # Get final stats
            stats = db.get_voter_stats(self.county)
            self.log(f"Final stats: {stats['total_voters']:,} total voters, "
                     f"{stats['geocoded_voters']:,} geocoded, "
                     f"{stats['ungeocoded_voters']:,} need geocoding")
            
            self.progress = 1.0
            self.status = 'completed'
            self.completed_at = datetime.now()
            elapsed = (self.completed_at - self.started_at).total_seconds()
            self.log(f"Registry import completed in {elapsed:.1f}s — "
                     f"{self.imported_count:,} voters imported")
            
        except Exception as e:
            self.status = 'failed'
            self.log(f"Registry import failed: {str(e)}")
            logger.exception(f"Registry import job {self.job_id} failed")
            raise
