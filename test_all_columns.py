"""Test script to verify all CSV columns are preserved in output."""
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from processor import ProcessingJob

def test_all_columns():
    """Test that all CSV columns are preserved in the output."""
    print("Testing CSV column preservation...")
    
    # Create processing job
    job = ProcessingJob(
        csv_path='test_complete_voter_data.csv',
        year='2024',
        county='Hidalgo',
        election_type='general',
        election_date='2024-11-05'
    )
    
    # Run processing
    print("\nRunning processing job...")
    job.run()
    
    # Check if job completed successfully
    if job.status != 'completed':
        print(f"❌ Job failed with status: {job.status}")
        for msg in job.log_messages:
            print(f"  {msg['message']}")
        return False
    
    print(f"✓ Job completed successfully")
    print(f"  Geocoded: {job.geocoded_count}")
    print(f"  Failed: {job.failed_count}")
    
    # Load the output file
    output_file = Path('data/map_data.json')
    if not output_file.exists():
        print(f"❌ Output file not found: {output_file}")
        return False
    
    with open(output_file, 'r') as f:
        map_data = json.load(f)
    
    print(f"\n✓ Output file loaded: {len(map_data['features'])} features")
    
    # Check first feature for all expected fields
    if not map_data['features']:
        print("❌ No features in output")
        return False
    
    first_feature = map_data['features'][0]
    props = first_feature['properties']
    
    print("\nChecking for expected fields in first feature:")
    
    expected_fields = [
        'id', 'vuid', 'cert', 'lastname', 'firstname', 
        'middlename', 'suffix', 'address', 'check_in', 
        'precinct', 'site', 'ballot_style', 'party', 'name'
    ]
    
    missing_fields = []
    present_fields = []
    
    for field in expected_fields:
        if field in props:
            present_fields.append(field)
            print(f"  ✓ {field}: {props[field]}")
        else:
            missing_fields.append(field)
            print(f"  ✗ {field}: MISSING")
    
    print(f"\nSummary:")
    print(f"  Present: {len(present_fields)}/{len(expected_fields)}")
    print(f"  Missing: {len(missing_fields)}/{len(expected_fields)}")
    
    if missing_fields:
        print(f"\n❌ Missing fields: {', '.join(missing_fields)}")
        return False
    
    print("\n✓ All expected fields are present!")
    return True

if __name__ == '__main__':
    success = test_all_columns()
    sys.exit(0 if success else 1)
