#!/usr/bin/env python3
"""
Upload district reference ZIP files and extract them on the server.
This script uses rsync which handles large files better than scp.
"""

import subprocess
import sys
from pathlib import Path

# Configuration
SERVER = "167.99.5.238"
SERVER_USER = "ubuntu"
LOCAL_DIR = Path("WhoVoted/data/district_reference")
REMOTE_DIR = "/home/ubuntu/WhoVoted/data/district_reference"

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        print(f"✓ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} - FAILED")
        print(f"Error: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def main():
    print("="*80)
    print("UPLOAD AND EXTRACT DISTRICT REFERENCE FILES")
    print("="*80)
    print()
    print(f"Server: {SERVER_USER}@{SERVER}")
    print(f"Local: {LOCAL_DIR}")
    print(f"Remote: {REMOTE_DIR}")
    print()
    
    # Check if local directory exists
    if not LOCAL_DIR.exists():
        print(f"✗ Error: Local directory not found: {LOCAL_DIR}")
        sys.exit(1)
    
    # Find ZIP files
    zip_files = list(LOCAL_DIR.glob("*all_files*.zip"))
    if not zip_files:
        print(f"✗ Error: No ZIP files found in {LOCAL_DIR}")
        sys.exit(1)
    
    print(f"Found {len(zip_files)} ZIP files:")
    for zf in zip_files:
        size_mb = zf.stat().st_size / (1024 * 1024)
        print(f"  - {zf.name} ({size_mb:.1f} MB)")
    print()
    
    # Upload each ZIP file using scp
    print("="*80)
    print("STEP 1: Uploading ZIP files")
    print("="*80)
    print()
    
    for zf in zip_files:
        cmd = [
            "scp",
            str(zf),
            f"{SERVER_USER}@{SERVER}:{REMOTE_DIR}/"
        ]
        
        if not run_command(cmd, f"Upload {zf.name}"):
            print(f"\n✗ Failed to upload {zf.name}")
            sys.exit(1)
    
    print("\n✓ All ZIP files uploaded successfully!")
    
    # Create extraction script
    extract_script = """#!/bin/bash
set -e

echo "============================================"
echo "EXTRACTING DISTRICT REFERENCE FILES"
echo "============================================"
echo ""

cd /home/ubuntu/WhoVoted/data/district_reference

# Install unzip if needed
if ! command -v unzip &> /dev/null; then
    echo "Installing unzip..."
    sudo apt-get update -qq
    sudo apt-get install -y unzip
fi

# Extract all ZIP files
echo "Extracting ZIP files..."
for zipfile in *all_files*.zip; do
    if [ -f "$zipfile" ]; then
        echo "  Extracting $zipfile..."
        unzip -o -q "$zipfile"
        echo "    Done"
    fi
done

echo ""
echo "Extraction complete!"
echo ""

# Count extracted files
echo "============================================"
echo "EXTRACTED FILES SUMMARY"
echo "============================================"
xls_count=$(ls -1 *.xls 2>/dev/null | wc -l)
pdf_count=$(ls -1 *.pdf 2>/dev/null | wc -l)
shp_count=$(ls -1 *.shp 2>/dev/null | wc -l)

echo "  XLS files: $xls_count"
echo "  PDF files: $pdf_count"
echo "  Shapefiles: $shp_count"
echo ""

# Show sample XLS files
echo "Sample XLS files:"
ls -lh *.xls 2>/dev/null | head -10

echo ""
echo "============================================"
echo "RUNNING PARSER"
echo "============================================"
echo ""

cd /home/ubuntu/WhoVoted

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q pandas xlrd openpyxl

# Run parser
echo "Running parser..."
python deploy/parse_district_files.py

echo ""
echo "============================================"
echo "VERIFICATION"
echo "============================================"
echo ""

# Check JSON files
echo "Generated JSON files:"
ls -lh data/district_reference/*.json 2>/dev/null

echo ""
echo "District counts:"
python3 -c "import json; f=open('data/district_reference/congressional_counties.json'); d=json.load(f); print('  Congressional:', len(d), 'districts')" 2>/dev/null || echo "  Congressional: Not found"
python3 -c "import json; f=open('data/district_reference/state_senate_counties.json'); d=json.load(f); print('  State Senate:', len(d), 'districts')" 2>/dev/null || echo "  State Senate: Not found"
python3 -c "import json; f=open('data/district_reference/state_house_counties.json'); d=json.load(f); print('  State House:', len(d), 'districts')" 2>/dev/null || echo "  State House: Not found"

echo ""
echo "============================================"
echo "COMPLETE!"
echo "============================================"
"""
    
    # Save extraction script locally
    script_path = Path("WhoVoted/deploy/extract_districts_temp.sh")
    script_path.write_text(extract_script)
    print(f"\n✓ Created extraction script: {script_path}")
    
    # Upload extraction script
    print("\n" + "="*80)
    print("STEP 2: Uploading extraction script")
    print("="*80)
    print()
    
    cmd = [
        "scp",
        str(script_path),
        f"{SERVER_USER}@{SERVER}:/tmp/extract_districts.sh"
    ]
    
    if not run_command(cmd, "Upload extraction script"):
        print("\n✗ Failed to upload extraction script")
        sys.exit(1)
    
    # Run extraction script on server
    print("\n" + "="*80)
    print("STEP 3: Running extraction on server")
    print("="*80)
    print()
    
    cmd = [
        "ssh",
        f"{SERVER_USER}@{SERVER}",
        "chmod +x /tmp/extract_districts.sh && /tmp/extract_districts.sh"
    ]
    
    if not run_command(cmd, "Extract and parse files"):
        print("\n✗ Failed to extract files")
        sys.exit(1)
    
    # Clean up local temp script
    script_path.unlink()
    
    print("\n" + "="*80)
    print("SUCCESS!")
    print("="*80)
    print()
    print("All district reference files have been:")
    print("  ✓ Uploaded to server")
    print("  ✓ Extracted from ZIP files")
    print("  ✓ Parsed into JSON files")
    print()
    print("The system can now reference these files for accurate district data!")
    print()

if __name__ == "__main__":
    main()
