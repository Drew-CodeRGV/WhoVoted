"""
Bug Condition Exploration Test for Year Display Issue

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Property 1: Fault Condition - Display Correct Year from Metadata
The system should read the year from metadata.json (2024) and use that value
for display and year tracking, not the system year (2026).
"""

import json
import os
from pathlib import Path

def test_metadata_contains_correct_year():
    """
    Test that metadata.json contains the correct year (2024).
    This should PASS - it confirms the metadata has the right data.
    """
    metadata_path = Path('public/data/metadata.json')
    
    assert metadata_path.exists(), "metadata.json should exist"
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    assert 'year' in metadata, "metadata.json should have 'year' field"
    assert metadata['year'] == '2024', f"metadata.json year should be '2024', got '{metadata['year']}'"
    
    print("✓ metadata.json contains correct year: 2024")


def test_system_year_is_2026():
    """
    Test that the current system year is 2026.
    This should PASS - it confirms we're in 2026.
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    assert current_year == 2026, f"System year should be 2026, got {current_year}"
    
    print(f"✓ System year is 2026")


def test_loadDefaultData_uses_system_year_not_metadata():
    """
    BUG CONDITION TEST - This should FAIL on unfixed code.
    
    Tests that loadDefaultData() correctly loads metadata.json FIRST
    and uses the year from it, rather than using system year as the primary source.
    
    EXPECTED OUTCOME: PASS after fix (confirms bug is fixed)
    """
    # Read the data.js file to check the implementation
    data_js_path = Path('public/data.js')
    
    with open(data_js_path, 'r') as f:
        data_js_content = f.read()
    
    # Check if it's in the loadDefaultData function
    loadDefaultData_start = data_js_content.find('async function loadDefaultData()')
    loadDefaultData_end = data_js_content.find('async function loadMetadata()', loadDefaultData_start)
    
    if loadDefaultData_start != -1 and loadDefaultData_end != -1:
        loadDefaultData_code = data_js_content[loadDefaultData_start:loadDefaultData_end]
        
        # Check that the function loads metadata FIRST
        loads_metadata_first = 'await fetch(\'data/metadata.json\')' in loadDefaultData_code or \
                               'await fetch("data/metadata.json")' in loadDefaultData_code
        
        # Check that it extracts year from metadata
        uses_metadata_year = 'metadata.year' in loadDefaultData_code
        
        # The fix should load metadata first and use its year
        assert loads_metadata_first, \
            "BUG DETECTED: loadDefaultData() should load metadata.json first"
        
        assert uses_metadata_year, \
            "BUG DETECTED: loadDefaultData() should use metadata.year"
    else:
        assert False, "Could not find loadDefaultData function"
    
    print("✓ loadDefaultData() correctly reads year from metadata (bug is fixed)")


def test_detectAvailableYears_uses_wrong_filename_pattern():
    """
    BUG CONDITION TEST - This should FAIL on unfixed code.
    
    Tests that detectAvailableYears() correctly checks metadata.json
    instead of only searching for map_data_{year}.json pattern.
    
    EXPECTED OUTCOME: PASS after fix (confirms bug is fixed)
    """
    # Read the data.js file to check the implementation
    data_js_path = Path('public/data.js')
    
    with open(data_js_path, 'r') as f:
        data_js_content = f.read()
    
    # Check if it's in the detectAvailableYears function
    detectAvailableYears_start = data_js_content.find('async function detectAvailableYears()')
    detectAvailableYears_end = data_js_content.find('async function loadDefaultData()', detectAvailableYears_start)
    
    if detectAvailableYears_start != -1 and detectAvailableYears_end != -1:
        detectAvailableYears_code = data_js_content[detectAvailableYears_start:detectAvailableYears_end]
        
        # Check that the function loads metadata.json
        checks_metadata = 'await fetch(\'data/metadata.json\')' in detectAvailableYears_code or \
                         'await fetch("data/metadata.json")' in detectAvailableYears_code
        
        # The fix should check metadata.json for the year
        assert checks_metadata, \
            "BUG DETECTED: detectAvailableYears() should check metadata.json for available years"
    else:
        assert False, "Could not find detectAvailableYears function"
    
    print("✓ detectAvailableYears() correctly checks metadata.json (bug is fixed)")


def test_actual_files_exist_with_correct_pattern():
    """
    Test that actual data files exist with the pattern map_data_{county}_{year}_{election_type}_{date}.json.
    This should PASS - it confirms the files exist.
    """
    data_dir = Path('public/data')
    
    # Look for files matching the pattern
    actual_files = list(data_dir.glob('map_data_*_2024_*.json'))
    
    assert len(actual_files) > 0, "Should have at least one file matching map_data_*_2024_*.json pattern"
    
    print(f"✓ Found {len(actual_files)} files with correct pattern:")
    for file in actual_files:
        print(f"  - {file.name}")


def test_simple_pattern_files_do_not_exist():
    """
    Test that files with pattern map_data_{year}.json do NOT exist.
    This should PASS - it confirms the simple pattern files don't exist.
    """
    data_dir = Path('public/data')
    
    # Check if map_data_2024.json exists
    simple_pattern_file = data_dir / 'map_data_2024.json'
    
    assert not simple_pattern_file.exists(), "map_data_2024.json should NOT exist (we use the full pattern)"
    
    print("✓ Simple pattern file map_data_2024.json does not exist (as expected)")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("BUG CONDITION EXPLORATION TEST")
    print("="*80)
    print("\nThese tests surface counterexamples that demonstrate the bug exists.")
    print("Tests marked as 'BUG CONDITION' should FAIL on unfixed code.\n")
    
    # Run baseline tests (should pass)
    print("\n--- BASELINE TESTS (should pass) ---")
    try:
        test_metadata_contains_correct_year()
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    
    try:
        test_system_year_is_2026()
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    
    try:
        test_actual_files_exist_with_correct_pattern()
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    
    try:
        test_simple_pattern_files_do_not_exist()
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    
    # Run bug condition tests (should fail on unfixed code)
    print("\n--- BUG CONDITION TESTS (should FAIL on unfixed code) ---")
    
    bug_detected = False
    
    try:
        test_loadDefaultData_uses_system_year_not_metadata()
    except AssertionError as e:
        print(f"✗ BUG CONFIRMED: {e}")
        bug_detected = True
    
    try:
        test_detectAvailableYears_uses_wrong_filename_pattern()
    except AssertionError as e:
        print(f"✗ BUG CONFIRMED: {e}")
        bug_detected = True
    
    print("\n" + "="*80)
    if bug_detected:
        print("RESULT: Bug condition tests FAILED (as expected - bug exists)")
        print("This confirms the bug exists and needs to be fixed.")
    else:
        print("RESULT: Bug condition tests PASSED (bug is fixed)")
        print("The fix has been successfully implemented.")
    print("="*80 + "\n")
