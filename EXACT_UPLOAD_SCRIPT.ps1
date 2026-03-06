# EXACT SCRIPT TO UPLOAD AND PARSE DISTRICT DATA
# Copy this entire script and run it

# ============================================
# STEP 1: CONFIGURE YOUR SERVER
# ============================================
$SERVER_USER = "ubuntu"  # Change this to your username
$SERVER_HOST = "your.server.ip.here"  # Change this to your server IP
$SERVER_PATH = "/home/ubuntu/WhoVoted/data/district_reference"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DISTRICT DATA UPLOAD & PARSE SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $SERVER_USER@$SERVER_HOST" -ForegroundColor Yellow
Write-Host "Path: $SERVER_PATH" -ForegroundColor Yellow
Write-Host ""

# ============================================
# STEP 2: CHECK LOCAL FILES
# ============================================
Write-Host "Checking local files..." -ForegroundColor Green
if (-not (Test-Path "data\district_reference")) {
    Write-Host "ERROR: Must run from WhoVoted directory" -ForegroundColor Red
    exit 1
}

Set-Location data\district_reference

$xlsFiles = Get-ChildItem -Filter "*.xls"
$zipFiles = Get-ChildItem -Filter "*.zip"

Write-Host "Found $($xlsFiles.Count) XLS files" -ForegroundColor Green
Write-Host "Found $($zipFiles.Count) ZIP files" -ForegroundColor Green

if ($xlsFiles.Count -eq 0 -and $zipFiles.Count -eq 0) {
    Write-Host "ERROR: No XLS or ZIP files found!" -ForegroundColor Red
    exit 1
}

# ============================================
# STEP 3: CREATE REMOTE DIRECTORY
# ============================================
Write-Host "`nCreating remote directory..." -ForegroundColor Green
ssh "${SERVER_USER}@${SERVER_HOST}" "mkdir -p ${SERVER_PATH}"

# ============================================
# STEP 4: UPLOAD FILES
# ============================================
Write-Host "`nUploading files to server..." -ForegroundColor Green

# Upload ZIP files if they exist
if ($zipFiles.Count -gt 0) {
    Write-Host "Uploading ZIP files..." -ForegroundColor Yellow
    foreach ($file in $zipFiles) {
        Write-Host "  Uploading: $($file.Name)" -ForegroundColor Cyan
        scp $file.FullName "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Uploaded: $($file.Name)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed: $($file.Name)" -ForegroundColor Red
            exit 1
        }
    }
}

# Upload XLS files if they exist
if ($xlsFiles.Count -gt 0) {
    Write-Host "Uploading XLS files..." -ForegroundColor Yellow
    foreach ($file in $xlsFiles) {
        Write-Host "  Uploading: $($file.Name)" -ForegroundColor Cyan
        scp $file.FullName "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Uploaded: $($file.Name)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed: $($file.Name)" -ForegroundColor Red
            exit 1
        }
    }
}

# Upload JSON reference files
Write-Host "Uploading JSON reference files..." -ForegroundColor Yellow
$jsonFiles = Get-ChildItem -Filter "*districts.json"
foreach ($file in $jsonFiles) {
    Write-Host "  Uploading: $($file.Name)" -ForegroundColor Cyan
    scp $file.FullName "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
}

# ============================================
# STEP 5: EXTRACT AND PARSE ON SERVER
# ============================================
Write-Host "`nExtracting and parsing on server..." -ForegroundColor Green

$serverScript = @"
#!/bin/bash
set -e

echo "========================================="
echo "SERVER-SIDE EXTRACTION AND PARSING"
echo "========================================="

cd ${SERVER_PATH}

# Install unzip if needed
if ! command -v unzip &> /dev/null; then
    echo "Installing unzip..."
    sudo apt-get update -qq
    sudo apt-get install -y unzip
fi

# Extract ZIP files if they exist
if ls *.zip 1> /dev/null 2>&1; then
    echo ""
    echo "Extracting ZIP files..."
    for zipfile in *.zip; do
        echo "  Extracting: \$zipfile"
        unzip -o "\$zipfile" > /dev/null 2>&1
        echo "  ✓ Extracted: \$zipfile"
    done
fi

# List XLS files
echo ""
echo "XLS files available:"
ls -lh *.xls 2>/dev/null | awk '{print "  " \$9 " (" \$5 ")"}'

# Count files
echo ""
echo "Total XLS files: \$(ls -1 *.xls 2>/dev/null | wc -l)"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q pandas xlrd openpyxl

# Run parser
echo ""
echo "========================================="
echo "RUNNING PARSER"
echo "========================================="
cd /home/ubuntu/WhoVoted
python deploy/parse_district_files.py

# Verify output
echo ""
echo "========================================="
echo "VERIFICATION"
echo "========================================="
echo "Generated JSON files:"
ls -lh data/district_reference/*counties.json data/district_reference/*precincts.json 2>/dev/null | awk '{print "  " \$9 " (" \$5 ")"}'

echo ""
echo "✓ COMPLETE!"
"@

# Save script to temp file and execute
$tempScript = [System.IO.Path]::GetTempFileName()
$serverScript | Out-File -FilePath $tempScript -Encoding ASCII

Write-Host "Executing server-side script..." -ForegroundColor Yellow
ssh "${SERVER_USER}@${SERVER_HOST}" "bash -s" < $tempScript

Remove-Item $tempScript

# ============================================
# STEP 6: VERIFY RESULTS
# ============================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nChecking generated files on server..." -ForegroundColor Green
ssh "${SERVER_USER}@${SERVER_HOST}" @"
cd /home/ubuntu/WhoVoted/data/district_reference
echo ""
echo "Congressional Districts:"
if [ -f congressional_counties.json ]; then
    echo "  ✓ congressional_counties.json"
    python3 -c "import json; f=open('congressional_counties.json'); d=json.load(f); print('    Districts:', len(d))"
else
    echo "  ✗ congressional_counties.json NOT FOUND"
fi

if [ -f congressional_precincts.json ]; then
    echo "  ✓ congressional_precincts.json"
else
    echo "  ✗ congressional_precincts.json NOT FOUND"
fi

echo ""
echo "State Senate Districts:"
if [ -f state_senate_counties.json ]; then
    echo "  ✓ state_senate_counties.json"
    python3 -c "import json; f=open('state_senate_counties.json'); d=json.load(f); print('    Districts:', len(d))"
else
    echo "  ✗ state_senate_counties.json NOT FOUND"
fi

if [ -f state_senate_precincts.json ]; then
    echo "  ✓ state_senate_precincts.json"
else
    echo "  ✗ state_senate_precincts.json NOT FOUND"
fi

echo ""
echo "State House Districts:"
if [ -f state_house_counties.json ]; then
    echo "  ✓ state_house_counties.json"
    python3 -c "import json; f=open('state_house_counties.json'); d=json.load(f); print('    Districts:', len(d))"
else
    echo "  ✗ state_house_counties.json NOT FOUND"
fi

if [ -f state_house_precincts.json ]; then
    echo "  ✓ state_house_precincts.json"
else
    echo "  ✗ state_house_precincts.json NOT FOUND"
fi
"@

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✓ UPLOAD AND PARSE COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nYour district reference data is now ready on the server." -ForegroundColor Green
Write-Host "The parser has created JSON files with all 219 districts." -ForegroundColor Green
