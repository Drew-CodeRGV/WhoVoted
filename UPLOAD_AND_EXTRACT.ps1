# ============================================
# UPLOAD AND EXTRACT DISTRICT REFERENCE FILES
# ============================================
# This script uploads ZIP files to the server and extracts them there

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP,
    
    [Parameter(Mandatory=$false)]
    [string]$ServerUser = "ubuntu"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "UPLOAD AND EXTRACT DISTRICT REFERENCE FILES" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$LocalDir = "WhoVoted\data\district_reference"
$RemoteDir = "/home/ubuntu/WhoVoted/data/district_reference"
$ServerAddress = "${ServerUser}@${ServerIP}"

# Check if local directory exists
if (-not (Test-Path $LocalDir)) {
    Write-Host "ERROR: Local directory not found: $LocalDir" -ForegroundColor Red
    exit 1
}

# Get list of ZIP files
$ZipFiles = Get-ChildItem -Path $LocalDir -Filter "*all_files*.zip"

if ($ZipFiles.Count -eq 0) {
    Write-Host "ERROR: No ZIP files found in $LocalDir" -ForegroundColor Red
    exit 1
}

Write-Host "Found $($ZipFiles.Count) ZIP files to upload:" -ForegroundColor Green
foreach ($file in $ZipFiles) {
    $sizeMB = [math]::Round($file.Length / 1MB, 2)
    Write-Host "  - $($file.Name) ($sizeMB MB)" -ForegroundColor White
}
Write-Host ""

# Step 1: Upload ZIP files
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 1: Uploading ZIP files to server..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

foreach ($file in $ZipFiles) {
    Write-Host "Uploading $($file.Name)..." -ForegroundColor Yellow
    
    $scpCommand = "scp `"$($file.FullName)`" ${ServerAddress}:${RemoteDir}/"
    Write-Host "  Command: $scpCommand" -ForegroundColor Gray
    
    try {
        & scp $file.FullName "${ServerAddress}:${RemoteDir}/"
        Write-Host "  SUCCESS: $($file.Name) uploaded" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to upload $($file.Name)" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

Write-Host "All ZIP files uploaded successfully!" -ForegroundColor Green
Write-Host ""

# Step 2: Create extraction script
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 2: Creating extraction script..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$ExtractScript = @'
#!/bin/bash
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
'@

# Save extraction script to temp file
$TempScript = [System.IO.Path]::GetTempFileName()
$ExtractScript | Out-File -FilePath $TempScript -Encoding ASCII -NoNewline

Write-Host "Extraction script created" -ForegroundColor Green
Write-Host ""

# Step 3: Upload and run extraction script
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 3: Running extraction on server..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

try {
    # Upload script
    Write-Host "Uploading extraction script..." -ForegroundColor Yellow
    & scp $TempScript "${ServerAddress}:/tmp/extract_districts.sh"
    
    # Make executable and run
    Write-Host "Running extraction script..." -ForegroundColor Yellow
    & ssh $ServerAddress "chmod +x /tmp/extract_districts.sh && /tmp/extract_districts.sh"
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "All district reference files have been:" -ForegroundColor Green
    Write-Host "  - Uploaded to server" -ForegroundColor White
    Write-Host "  - Extracted from ZIP files" -ForegroundColor White
    Write-Host "  - Parsed into JSON files" -ForegroundColor White
    Write-Host ""
    Write-Host "The system can now reference these files for accurate district data!" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "ERROR: Failed to run extraction script" -ForegroundColor Red
    Write-Host "$_" -ForegroundColor Red
    exit 1
} finally {
    # Clean up temp file
    Remove-Item -Path $TempScript -Force -ErrorAction SilentlyContinue
}
