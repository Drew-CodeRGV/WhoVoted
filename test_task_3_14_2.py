"""
Unit tests for task 3.14.2: deploy_outputs() method for year-specific deployment
"""
import pytest
import json
import shutil
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from processor import ProcessingJob
from config import Config


@pytest.fixture
def setup_test_dirs(tmp_path):
    """Set up temporary directories for testing."""
    # Create temporary directories
    data_dir = tmp_path / "data"
    public_dir = tmp_path / "public"
    data_dir.mkdir()
    public_dir.mkdir()
    
    # Override Config paths
    original_data_dir = Config.DATA_DIR
    original_public_dir = Config.PUBLIC_DIR
    Config.DATA_DIR = data_dir
    Config.PUBLIC_DIR = public_dir
    
    yield data_dir, public_dir
    
    # Restore original paths
    Config.DATA_DIR = original_data_dir
    Config.PUBLIC_DIR = original_public_dir


@pytest.fixture
def create_test_files(setup_test_dirs):
    """Create test output files in data directory."""
    data_dir, public_dir = setup_test_dirs
    
    # Create year-specific files
    map_data_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-98.1630, 26.1906]},
                "properties": {"address": "123 Main St"}
            }
        ]
    }
    
    metadata_content = {
        "year": "2024",
        "county": "Hidalgo",
        "election_type": "general",
        "election_date": "2024-11-05"
    }
    
    # Year-specific filenames
    map_data_specific = data_dir / "map_data_Hidalgo_2024_general_20241105.json"
    metadata_specific = data_dir / "metadata_Hidalgo_2024_general_20241105.json"
    
    with open(map_data_specific, 'w') as f:
        json.dump(map_data_content, f)
    
    with open(metadata_specific, 'w') as f:
        json.dump(metadata_content, f)
    
    # Default files for backward compatibility
    map_data_default = data_dir / "map_data.json"
    metadata_default = data_dir / "metadata.json"
    
    with open(map_data_default, 'w') as f:
        json.dump(map_data_content, f)
    
    with open(metadata_default, 'w') as f:
        json.dump(metadata_content, f)
    
    return data_dir, public_dir


def test_deploy_year_specific_files(create_test_files):
    """Test that year-specific files are deployed to public/data/ directory."""
    data_dir, public_dir = create_test_files
    
    # Create a processing job
    job = ProcessingJob(
        csv_path="dummy.csv",
        year="2024",
        county="Hidalgo",
        election_type="general",
        election_date="2024-11-05"
    )
    
    # Deploy outputs
    job.deploy_outputs()
    
    # Verify year-specific files were deployed
    public_data_dir = public_dir / "data"
    assert public_data_dir.exists(), "public/data directory should exist"
    
    map_data_deployed = public_data_dir / "map_data_Hidalgo_2024_general_20241105.json"
    metadata_deployed = public_data_dir / "metadata_Hidalgo_2024_general_20241105.json"
    
    assert map_data_deployed.exists(), "Year-specific map_data file should be deployed"
    assert metadata_deployed.exists(), "Year-specific metadata file should be deployed"
    
    # Verify content
    with open(map_data_deployed) as f:
        content = json.load(f)
        assert content["type"] == "FeatureCollection"
        assert len(content["features"]) == 1


def test_deploy_backward_compatible_files(create_test_files):
    """Test that backward-compatible default files are also deployed."""
    data_dir, public_dir = create_test_files
    
    # Create a processing job
    job = ProcessingJob(
        csv_path="dummy.csv",
        year="2024",
        county="Hidalgo",
        election_type="general",
        election_date="2024-11-05"
    )
    
    # Deploy outputs
    job.deploy_outputs()
    
    # Verify default files were deployed
    public_data_dir = public_dir / "data"
    
    map_data_default = public_data_dir / "map_data.json"
    metadata_default = public_data_dir / "metadata.json"
    
    assert map_data_default.exists(), "Default map_data.json should be deployed"
    assert metadata_default.exists(), "Default metadata.json should be deployed"
    
    # Verify content
    with open(map_data_default) as f:
        content = json.load(f)
        assert content["type"] == "FeatureCollection"


def test_deploy_creates_public_data_directory(setup_test_dirs):
    """Test that deploy_outputs creates public/data/ directory if it doesn't exist."""
    data_dir, public_dir = setup_test_dirs
    
    # Create minimal test files
    map_data_content = {"type": "FeatureCollection", "features": []}
    
    map_data_specific = data_dir / "map_data_Cameron_2026_primary_20260303.json"
    map_data_default = data_dir / "map_data.json"
    metadata_specific = data_dir / "metadata_Cameron_2026_primary_20260303.json"
    metadata_default = data_dir / "metadata.json"
    
    for filepath in [map_data_specific, map_data_default, metadata_specific, metadata_default]:
        with open(filepath, 'w') as f:
            json.dump(map_data_content, f)
    
    # Create a processing job
    job = ProcessingJob(
        csv_path="dummy.csv",
        year="2026",
        county="Cameron",
        election_type="primary",
        election_date="2026-03-03"
    )
    
    # Verify public/data doesn't exist yet
    public_data_dir = public_dir / "data"
    assert not public_data_dir.exists()
    
    # Deploy outputs
    job.deploy_outputs()
    
    # Verify directory was created
    assert public_data_dir.exists(), "public/data directory should be created"


def test_deploy_with_different_counties(setup_test_dirs):
    """Test deployment with different county names."""
    data_dir, public_dir = setup_test_dirs
    
    counties = ["Hidalgo", "Cameron", "Travis"]
    
    for county in counties:
        # Create test files for this county
        map_data_content = {"type": "FeatureCollection", "features": []}
        
        map_data_specific = data_dir / f"map_data_{county}_2024_general_20241105.json"
        metadata_specific = data_dir / f"metadata_{county}_2024_general_20241105.json"
        map_data_default = data_dir / "map_data.json"
        metadata_default = data_dir / "metadata.json"
        
        for filepath in [map_data_specific, metadata_specific, map_data_default, metadata_default]:
            with open(filepath, 'w') as f:
                json.dump(map_data_content, f)
        
        # Create job and deploy
        job = ProcessingJob(
            csv_path="dummy.csv",
            year="2024",
            county=county,
            election_type="general",
            election_date="2024-11-05"
        )
        
        job.deploy_outputs()
        
        # Verify files were deployed
        public_data_dir = public_dir / "data"
        deployed_file = public_data_dir / f"map_data_{county}_2024_general_20241105.json"
        assert deployed_file.exists(), f"File for {county} should be deployed"


def test_deploy_logs_warnings_for_missing_files(setup_test_dirs):
    """Test that deploy_outputs logs warnings when files are missing."""
    data_dir, public_dir = setup_test_dirs
    
    # Don't create any files - they should be missing
    
    # Create a processing job
    job = ProcessingJob(
        csv_path="dummy.csv",
        year="2024",
        county="Hidalgo",
        election_type="general",
        election_date="2024-11-05"
    )
    
    # Deploy outputs (should log warnings)
    job.deploy_outputs()
    
    # Check that warnings were logged
    log_messages = [msg['message'] for msg in job.log_messages]
    
    # Should have warnings for missing files
    warning_count = sum(1 for msg in log_messages if 'Warning' in msg and 'not found' in msg)
    assert warning_count > 0, "Should log warnings for missing files"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
