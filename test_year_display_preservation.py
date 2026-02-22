"""
Preservation Property Tests for Year Display Fix

These tests capture baseline behavior that should remain unchanged after the fix.
Run these tests on UNFIXED code first to establish baseline, then verify they
still pass after implementing the fix.

Property 2: Preservation - Existing Data Loading Behavior
All functionality that does NOT involve determining or displaying the year
should be completely unaffected by the fix.
"""

import json
from pathlib import Path

def test_map_data_structure_preserved():
    """
    Test that map_data.json has the correct GeoJSON structure.
    This should PASS on both unfixed and fixed code.
    """
    map_data_path = Path('public/data/map_data.json')
    
    assert map_data_path.exists(), "map_data.json should exist"
    
    with open(map_data_path, 'r') as f:
        map_data = json.load(f)
    
    # Check GeoJSON structure
    assert map_data['type'] == 'FeatureCollection', "Should be a FeatureCollection"
    assert 'features' in map_data, "Should have features array"
    assert isinstance(map_data['features'], list), "Features should be a list"
    assert len(map_data['features']) > 0, "Should have at least one feature"
    
    # Check first feature structure
    first_feature = map_data['features'][0]
    assert first_feature['type'] == 'Feature', "Feature should have type 'Feature'"
    assert 'geometry' in first_feature, "Feature should have geometry"
    assert 'properties' in first_feature, "Feature should have properties"
    assert first_feature['geometry']['type'] == 'Point', "Geometry should be Point"
    assert 'coordinates' in first_feature['geometry'], "Geometry should have coordinates"
    
    print(f"✓ map_data.json structure preserved ({len(map_data['features'])} features)")


def test_voter_data_fields_preserved():
    """
    Test that voter data fields are preserved in the output.
    This should PASS on both unfixed and fixed code.
    """
    map_data_path = Path('public/data/map_data.json')
    
    with open(map_data_path, 'r') as f:
        map_data = json.load(f)
    
    # Check first feature properties
    first_feature = map_data['features'][0]
    properties = first_feature['properties']
    
    # Required fields
    assert 'address' in properties, "Should have address"
    assert 'precinct' in properties, "Should have precinct"
    assert 'ballot_style' in properties, "Should have ballot_style"
    
    # Check that coordinates are valid
    coords = first_feature['geometry']['coordinates']
    assert len(coords) == 2, "Coordinates should have 2 elements [lng, lat]"
    assert isinstance(coords[0], (int, float)), "Longitude should be a number"
    assert isinstance(coords[1], (int, float)), "Latitude should be a number"
    
    print("✓ Voter data fields preserved in output")


def test_metadata_fields_preserved():
    """
    Test that metadata fields (other than year) are preserved.
    This should PASS on both unfixed and fixed code.
    """
    metadata_path = Path('public/data/metadata.json')
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Check non-year fields
    assert 'county' in metadata, "Should have county field"
    assert 'election_type' in metadata, "Should have election_type field"
    assert 'election_date' in metadata, "Should have election_date field"
    assert 'last_updated' in metadata, "Should have last_updated field"
    assert 'total_addresses' in metadata, "Should have total_addresses field"
    assert 'successfully_geocoded' in metadata, "Should have successfully_geocoded field"
    
    print("✓ Metadata fields (other than year) preserved")


def test_party_affiliation_fields_preserved():
    """
    Test that party affiliation fields are preserved in the output.
    This should PASS on both unfixed and fixed code.
    """
    map_data_path = Path('public/data/map_data.json')
    
    with open(map_data_path, 'r') as f:
        map_data = json.load(f)
    
    # Check first feature properties
    first_feature = map_data['features'][0]
    properties = first_feature['properties']
    
    # Party affiliation fields
    assert 'party_affiliation_current' in properties, "Should have party_affiliation_current"
    assert 'party_history' in properties, "Should have party_history"
    assert 'has_switched_parties' in properties, "Should have has_switched_parties"
    assert 'voted_in_current_election' in properties, "Should have voted_in_current_election"
    assert 'is_registered' in properties, "Should have is_registered"
    
    print("✓ Party affiliation fields preserved")


def test_optional_voter_fields_preserved():
    """
    Test that optional voter fields (ID, CERT, name components, etc.) are preserved.
    This should PASS on both unfixed and fixed code.
    """
    map_data_path = Path('public/data/map_data.json')
    
    with open(map_data_path, 'r') as f:
        map_data = json.load(f)
    
    # Find a feature with optional fields
    feature_with_optional_fields = None
    for feature in map_data['features']:
        if 'party' in feature['properties']:
            feature_with_optional_fields = feature
            break
    
    assert feature_with_optional_fields is not None, "Should have at least one feature with optional fields"
    
    properties = feature_with_optional_fields['properties']
    
    # Check that party field is preserved (raw value from CSV)
    assert 'party' in properties, "Should have party field (raw value from CSV)"
    
    print("✓ Optional voter fields preserved")


def test_data_js_functions_exist():
    """
    Test that key functions exist in data.js.
    This should PASS on both unfixed and fixed code.
    """
    data_js_path = Path('public/data.js')
    
    with open(data_js_path, 'r') as f:
        data_js_content = f.read()
    
    # Check that key functions exist
    assert 'async function loadMapData()' in data_js_content, "loadMapData function should exist"
    assert 'async function detectAvailableYears()' in data_js_content, "detectAvailableYears function should exist"
    assert 'async function loadDefaultData()' in data_js_content, "loadDefaultData function should exist"
    assert 'async function loadMetadata()' in data_js_content, "loadMetadata function should exist"
    assert 'function parseVoterData(' in data_js_content, "parseVoterData function should exist"
    
    print("✓ Key functions exist in data.js")


def test_precinct_boundaries_files_preserved():
    """
    Test that precinct boundary files are preserved.
    This should PASS on both unfixed and fixed code.
    """
    data_dir = Path('public/data')
    
    # Check for precinct boundary files
    precinct_files = [
        'precinct_boundaries.json',
        'precinct_boundaries_cameron.json',
        'precinct_boundaries_combined.json'
    ]
    
    for filename in precinct_files:
        file_path = data_dir / filename
        assert file_path.exists(), f"{filename} should exist"
    
    print("✓ Precinct boundary files preserved")


def test_voting_locations_file_preserved():
    """
    Test that voting_locations.json file is preserved.
    This should PASS on both unfixed and fixed code.
    """
    voting_locations_path = Path('public/data/voting_locations.json')
    
    assert voting_locations_path.exists(), "voting_locations.json should exist"
    
    with open(voting_locations_path, 'r') as f:
        voting_locations = json.load(f)
    
    # Check structure (it's an object with a locations array)
    assert isinstance(voting_locations, dict), "voting_locations should be a dict"
    assert 'locations' in voting_locations, "Should have locations array"
    assert isinstance(voting_locations['locations'], list), "locations should be a list"
    
    print(f"✓ voting_locations.json preserved ({len(voting_locations['locations'])} locations)")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("PRESERVATION PROPERTY TESTS")
    print("="*80)
    print("\nThese tests capture baseline behavior that should remain unchanged.")
    print("Run on UNFIXED code first, then verify they still pass after the fix.\n")
    
    all_passed = True
    
    tests = [
        test_map_data_structure_preserved,
        test_voter_data_fields_preserved,
        test_metadata_fields_preserved,
        test_party_affiliation_fields_preserved,
        test_optional_voter_fields_preserved,
        test_data_js_functions_exist,
        test_precinct_boundaries_files_preserved,
        test_voting_locations_file_preserved,
    ]
    
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ FAILED: {test.__name__}: {e}")
            all_passed = False
        except Exception as e:
            print(f"✗ ERROR: {test.__name__}: {e}")
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("RESULT: All preservation tests PASSED")
        print("Baseline behavior is captured and should be preserved after the fix.")
    else:
        print("RESULT: Some preservation tests FAILED")
        print("Review failures to ensure baseline behavior is correctly captured.")
    print("="*80 + "\n")
