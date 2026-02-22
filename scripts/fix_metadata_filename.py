#!/usr/bin/env python3
"""
Script to add original_filename field to existing metadata files.
"""

import json
import sys
from pathlib import Path

def fix_metadata_file(filepath):
    """Add original_filename field if missing."""
    print(f"\nProcessing: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check if original_filename already exists
        if 'original_filename' in metadata and metadata['original_filename']:
            print(f"  ℹ️  Already has original_filename: {metadata['original_filename']}")
            return True
        
        # Generate a descriptive filename based on metadata
        county = metadata.get('county', 'Unknown')
        year = metadata.get('year', 'Unknown')
        election_type = metadata.get('election_type', 'Unknown')
        election_date = metadata.get('election_date', 'Unknown')
        voting_method = metadata.get('voting_method', 'early-voting')
        
        # Create a descriptive filename
        filename = f"{county}_{year}_{election_type}_{election_date}_{voting_method}.csv"
        metadata['original_filename'] = filename
        
        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  ✓ Added original_filename: {filename}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Find and fix all metadata JSON files."""
    print("=" * 60)
    print("Metadata Filename Fixer")
    print("=" * 60)
    
    # Find all metadata files in both public/data and data directories
    directories = [
        Path('WhoVoted/public/data'),
        Path('WhoVoted/data')
    ]
    
    all_metadata_files = []
    for directory in directories:
        if directory.exists():
            all_metadata_files.extend(list(directory.glob('metadata*.json')))
    
    if not all_metadata_files:
        print("No metadata files found")
        sys.exit(0)
    
    print(f"\nFound {len(all_metadata_files)} metadata files to process\n")
    
    success_count = 0
    for filepath in sorted(all_metadata_files):
        if fix_metadata_file(filepath):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Completed: {success_count}/{len(all_metadata_files)} files processed successfully")
    print("=" * 60)

if __name__ == '__main__':
    main()
