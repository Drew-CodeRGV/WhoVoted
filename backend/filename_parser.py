"""Filename parser for extracting election metadata from uploaded files."""
import re
from datetime import datetime
from typing import Optional

class FilenameParser:
    """Parse election metadata from standardized filenames."""
    
    # Party mappings
    PARTY_MAP = {
        'REP': 'Republican',
        'REPUBLICAN': 'Republican',
        'DEM': 'Democratic',
        'DEMOCRAT': 'Democratic',
        'DEMOCRATIC': 'Democratic',
        'LIB': 'Libertarian',
        'LIBERTARIAN': 'Libertarian',
        'GRN': 'Green',
        'GREEN': 'Green',
        'IND': 'Independent',
        'INDEPENDENT': 'Independent'
    }
    
    # Election type mappings
    ELECTION_TYPE_MAP = {
        'PRIMARY': 'primary',
        'RUNOFF': 'runoff',
        'GENERAL': 'general',
        'SPECIAL': 'special',
        'EV': 'early-voting',
        'EARLY VOTING': 'early-voting',
        'EARLY-VOTING': 'early-voting'
    }
    
    @staticmethod
    def parse_filename(filename: str) -> dict:
        """
        Parse election metadata from filename.
        
        Expected format examples:
        - "2024 Primary EV REP (Cumulative)_202403020808348828.csv"
        - "2024_General_DEM_20241105.csv"
        - "Hidalgo_2024_Primary_Republican_EarlyVoting.csv"
        
        Args:
            filename: Original filename (with or without extension)
        
        Returns:
            Dictionary with extracted metadata:
            {
                'year': str,
                'election_type': str,
                'party': str,
                'is_early_voting': bool,
                'is_cumulative': bool,
                'timestamp': str (ISO format),
                'county': str or None
            }
        """
        # Remove file extension
        name = filename.replace('.csv', '').replace('.CSV', '')
        
        # Initialize result
        result = {
            'year': None,
            'election_type': None,
            'party': None,
            'is_early_voting': False,
            'is_cumulative': False,
            'timestamp': None,
            'county': None
        }
        
        # Extract year (4-digit number starting with 20, prioritize earlier matches)
        # Look for year that's NOT part of a longer timestamp
        year_matches = []
        
        # First, try to find standalone year (not part of timestamp)
        # Match year that's followed by space, underscore, or word boundary
        standalone_year = re.search(r'(?:^|_|\s)(20\d{2})(?=\s|_|$|\s)', name)
        if standalone_year:
            year_matches.append(standalone_year.group(1))
        
        # If no standalone year found, look for any 4-digit year
        if not year_matches:
            year_matches = re.findall(r'(20\d{2})', name)
        
        if year_matches:
            # Use the first year found in the filename
            result['year'] = year_matches[0]
        
        # Extract party affiliation
        name_upper = name.upper()
        for party_code, party_name in FilenameParser.PARTY_MAP.items():
            # Use word boundary or underscore/space boundary
            pattern = r'(?:^|_|\s)' + party_code + r'(?:$|_|\s)'
            if re.search(pattern, name_upper):
                result['party'] = party_name
                break
        
        # Extract election type (check in order of specificity)
        election_types_ordered = [
            ('PRIMARY', 'primary'),
            ('RUNOFF', 'runoff'),
            ('GENERAL', 'general'),
            ('SPECIAL', 'special')
        ]
        
        for type_code, type_name in election_types_ordered:
            pattern = r'(?:^|_|\s)' + type_code + r'(?:$|_|\s)'
            if re.search(pattern, name_upper):
                result['election_type'] = type_name
                break
        
        # Check for early voting indicators
        ev_patterns = [
            r'(?:^|_|\s)EV(?:$|_|\s)',
            r'EARLY[\s_-]*VOTING',
            r'EARLYVOTING'
        ]
        for pattern in ev_patterns:
            if re.search(pattern, name_upper):
                result['is_early_voting'] = True
                break
        
        # Check for cumulative indicator
        if re.search(r'\b(CUMULATIVE|CUMUL|TOTAL|AGGREGATE)\b', name_upper):
            result['is_cumulative'] = True
        
        # Extract timestamp from end of filename
        # Format: YYYYMMDDHHMMSSSSSS (20 digits)
        timestamp_match = re.search(r'_?(\d{14,20})$', name)
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            try:
                # Parse first 14 digits as YYYYMMDDHHmmss
                dt = datetime.strptime(timestamp_str[:14], '%Y%m%d%H%M%S')
                result['timestamp'] = dt.isoformat()
                
                # Extract date for election_date (but don't override year from filename)
                result['election_date'] = dt.strftime('%Y-%m-%d')
            except ValueError:
                # Try shorter format YYYYMMDD
                try:
                    dt = datetime.strptime(timestamp_str[:8], '%Y%m%d')
                    result['timestamp'] = dt.isoformat()
                    result['election_date'] = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass
        
        # Extract county name (common Texas counties)
        texas_counties = [
            'HIDALGO', 'CAMERON', 'HARRIS', 'DALLAS', 'TARRANT', 'BEXAR',
            'TRAVIS', 'COLLIN', 'DENTON', 'EL PASO', 'FORT BEND', 'MONTGOMERY',
            'WILLIAMSON', 'NUECES', 'GALVESTON', 'BRAZORIA', 'WEBB'
        ]
        
        for county in texas_counties:
            if re.search(r'\b' + county + r'\b', name_upper):
                result['county'] = county.title()
                break
        
        # Default values if not found
        if not result['year']:
            result['year'] = str(datetime.now().year)
        
        if not result['election_type']:
            result['election_type'] = 'general'
        
        if not result['county']:
            result['county'] = 'Unknown'
        
        return result
    
    @staticmethod
    def format_election_description(metadata: dict) -> str:
        """
        Format a human-readable election description from metadata.
        
        Args:
            metadata: Dictionary from parse_filename()
        
        Returns:
            Formatted description string
        """
        parts = []
        
        if metadata['year']:
            parts.append(metadata['year'])
        
        if metadata['party']:
            parts.append(metadata['party'])
        
        if metadata['election_type']:
            parts.append(metadata['election_type'].replace('-', ' ').title())
        
        if metadata['is_early_voting']:
            parts.append('Early Voting')
        
        if metadata['is_cumulative']:
            parts.append('(Cumulative)')
        
        return ' '.join(parts)
    
    @staticmethod
    def get_party_color(party: str) -> str:
        """
        Get color code for party affiliation.
        
        Args:
            party: Party name (e.g., 'Republican', 'Democratic')
        
        Returns:
            Color code (e.g., 'red', 'blue')
        """
        party_colors = {
            'Republican': 'red',
            'Democratic': 'blue',
            'Libertarian': 'gold',
            'Green': 'green',
            'Independent': 'purple'
        }
        
        return party_colors.get(party, 'gray')


def test_parser():
    """Test the filename parser with example filenames."""
    test_cases = [
        "2024 Primary EV REP (Cumulative)_202403020808348828.csv",
        "2024_General_DEM_20241105.csv",
        "Hidalgo_2024_Primary_Republican_EarlyVoting.csv",
        "Cameron_County_2024_Runoff_Democratic.csv",
        "2024_Special_Election_Independent_20240615.csv"
    ]
    
    print("Testing Filename Parser:")
    print("=" * 80)
    
    for filename in test_cases:
        print(f"\nFilename: {filename}")
        metadata = FilenameParser.parse_filename(filename)
        print(f"  Year: {metadata['year']}")
        print(f"  Election Type: {metadata['election_type']}")
        print(f"  Party: {metadata['party']}")
        print(f"  Early Voting: {metadata['is_early_voting']}")
        print(f"  Cumulative: {metadata['is_cumulative']}")
        print(f"  Timestamp: {metadata['timestamp']}")
        print(f"  County: {metadata['county']}")
        print(f"  Description: {FilenameParser.format_election_description(metadata)}")
        print(f"  Color: {FilenameParser.get_party_color(metadata['party'])}")


if __name__ == '__main__':
    test_parser()
