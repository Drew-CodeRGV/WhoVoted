"""Test for task 3.14.1: metadata-aware filename generation."""
import json
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from processor import ProcessingJob
from config import Config

def test_metadata_aware_filenames():
    """Test that generate_outputs creates files with metadata-aware names."""
    
    # Create temporary directories
    temp_dir = Path(tempfile.mkdtemp())
    data_dir = temp_dir / 'data'
    data_dir.mkdir()
    
    # Override Config paths for testing
    original_data_dir = Config.DATA_DIR
    Config.DATA_DIR = data_dir
    
    try:
        # Create test data
        test_data = pd.DataFrame([
            {
                'lat': 26.1906,
                'lng': -98.1630,
                'display_name': '123 Main St, McAllen, TX',
                'original_address': '123 MAIN ST',
                'precinct': '101',
                'ballot_style': 'A',
                'vuid': '1234567890'
            },
            {
                'lat': 26.2034,
                'lng': -98.2300,
                'display_name': '456 Oak Ave, McAllen, TX',
                'original_address': '456 OAK AVE',
                'precinct': '102',
                'ballot_style': 'B',
                'vuid': '0987654321'
            }
        ])
        
        # Create a processing job with metadata
        job = ProcessingJob(
            csv_path='dummy.csv',
            county='Cameron',
            year='2026',
            election_type='primary',
            election_date='2026-03-03'
        )
        job.total_records = 2
        job.geocoded_count = 2
        job.failed_count = 0
        
        # Generate outputs
        job.generate_outputs(test_data)
        
        # Check that metadata-aware files were created
        expected_map_filename = 'map_data_Cameron_2026_primary_20260303.json'
        expected_metadata_filename = 'metadata_Cameron_2026_primary_20260303.json'
        
        map_file_path = data_dir / expected_map_filename
        metadata_file_path = data_dir / expected_metadata_filename
        
        assert map_file_path.exists(), f"Expected map file not found: {expected_map_filename}"
        assert metadata_file_path.exists(), f"Expected metadata file not found: {expected_metadata_filename}"
        
        # Check backward compatibility files
        assert (data_dir / 'map_data.json').exists(), "Backward compatibility map_data.json not found"
        assert (data_dir / 'metadata.json').exists(), "Backward compatibility metadata.json not found"
        
        # Verify map_data content
        with open(map_file_path, 'r') as f:
            map_data = json.load(f)
        
        assert map_data['type'] == 'FeatureCollection'
        assert len(map_data['features']) == 2
        
        # Check that VUID is included in properties
        feature1 = map_data['features'][0]
        assert 'vuid' in feature1['properties'], "VUID not found in feature properties"
        assert feature1['properties']['vuid'] == '1234567890'
        
        feature2 = map_data['features'][1]
        assert 'vuid' in feature2['properties'], "VUID not found in feature properties"
        assert feature2['properties']['vuid'] == '0987654321'
        
        # Verify metadata content
        with open(metadata_file_path, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['county'] == 'Cameron', "County not in metadata"
        assert metadata['year'] == '2026', "Year not in metadata"
        assert metadata['election_type'] == 'primary', "Election type not in metadata"
        assert metadata['election_date'] == '2026-03-03', "Election date not in metadata"
        assert metadata['total_addresses'] == 2
        assert metadata['successfully_geocoded'] == 2
        assert metadata['failed_addresses'] == 0
        
        print("✓ All tests passed!")
        print(f"✓ Created file: {expected_map_filename}")
        print(f"✓ Created file: {expected_metadata_filename}")
        print(f"✓ VUID included in GeoJSON properties")
        print(f"✓ Metadata includes county, year, election_type, election_date")
        print(f"✓ Backward compatibility files created")
        
    finally:
        # Restore original config
        Config.DATA_DIR = original_data_dir
        
        # Clean up
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    test_metadata_aware_filenames()
