# UPLOAD ALL DISTRICT ZIP FILES TO SERVER
# This uploads all 3 large ZIP files and extracts them as permanent references

# ============================================
# CONFIGURE YOUR SERVER
# ============================================
$SERVER_USER = "ubuntu"  # Change this
$SERVER_HOST = "your.server.ip"  # Change this
$SERVER_PATH = "/home/ubuntu/WhoVoted/data/district_reference"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "UPLOAD ALL DISTRICT ZIP FILES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $SERVER_USER@$SERVER_HOST" -ForegroundColor Yellow
Write-Host "Path: $SERVER_PATH" -ForegroundColor Yellow
Write-Host ""

# Check we're in the right place
if (-not (Test-Path "data\district_reference")) {
    Write-Host "ERROR: Must run from WhoVoted directory" -ForegroundColor Red
    exit 1
}

cd data\district_reference

# Find all ZIP files
$zipFiles = Get-ChildItem -Filter "*All_Files*.zip"

if ($zipFiles.Count -eq 0) {
    Write-Host "ERROR: No ZIP files found!" -ForegroundColor Red
    Write-Host "Looking for:" -ForegroundColor Yellow
    Write-Host "  - PLANC2333_All_Files_*.zip (Congressional)" -ForegroundColor Yellow
    Write-Host "  - PLANS2168_All_Files_*.zip (State Senate)" -ForegroundColor Yellow
    Write-Host "  - PLANH2316_All_Files_*.zip (State House)" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found $($zipFiles.Count) ZIP file(s):" -ForegroundColor Green
foreach ($file in $zipFiles) {
    $sizeMB = [math]::Round($file.Length/1MB, 2)
    Write-Host "  - $($file.Name) ($sizeMB MB)" -ForegroundColor Cyan
}

# Create remote directory
Write-Host "`nCreating remote directory..." -ForegroundColor Green
ssh "${SERVER_USER}@${SERVER_HOST}" "mkdir -p ${SERVER_PATH}"

# Upload each ZIP file
Write-Host "`nUploading ZIP files..." -ForegroundColor Green
foreach ($file in $zipFiles) {
    Write-Host "`nUploading: $($file.Name)" -ForegroundColor Yellow
    Write-Host "  Size: $([math]::Round($file.Length/1MB, 2)) MB" -ForegroundColor Gray
    
    scp $file.FullName "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Uploaded successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Upload failed!" -ForegroundColor Red
        exit 1
    }
}

# Extract on server
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "EXTRACTING FILES ON SERVER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$serverScript = @"
#!/bin/bash
set -e

echo ""
echo "Installing unzip if needed..."
if ! command -v unzip &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y unzip
fi

cd ${SERVER_PATH}

echo ""
echo "Extracting ZIP files..."
for zipfile in *All_Files*.zip; do
    if [ -f "\$zipfile" ]; then
        echo ""
        echo "Extracting: \$zipfile"
        unzip -o "\$zipfile"
        echo "✓ Extracted: \$zipfile"
    fi
done

echo ""
echo "========================================="
echo "FILE SUMMARY"
echo "========================================="

echo ""
echo "ZIP files:"
ls -lh *All_Files*.zip 2>/dev/null | awk '{print "  " \$9 " (" \$5 ")"}'

echo ""
echo "XLS files (first 20):"
ls -lh *.xls 2>/dev/null | head -20 | awk '{print "  " \$9 " (" \$5 ")"}'

echo ""
echo "Total XLS files: \$(ls -1 *.xls 2>/dev/null | wc -l)"

echo ""
echo "PDF files: \$(ls -1 *.pdf 2>/dev/null | wc -l)"

echo ""
echo "Shapefiles: \$(ls -1 *.shp 2>/dev/null | wc -l)"

echo ""
echo "========================================="
echo "RUNNING PARSER"
echo "========================================="

cd /home/ubuntu/WhoVoted

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q pandas xlrd openpyxl

# Run parser
echo ""
python deploy/parse_district_files.py

echo ""
echo "========================================="
echo "VERIFICATION"
echo "========================================="

cd data/district_reference

echo ""
echo "Generated JSON files:"
for jsonfile in *counties.json *precincts.json; do
    if [ -f "\$jsonfile" ]; then
        size=\$(ls -lh "\$jsonfile" | awk '{print \$5}')
        count=\$(python3 -c "import json; f=open('\$jsonfile'); d=json.load(f); print(len(d))" 2>/dev/null || echo "?")
        echo "  ✓ \$jsonfile (\$size, \$count districts)"
    fi
done

echo ""
echo "========================================="
echo "✓ COMPLETE!"
echo "========================================="
echo ""
echo "All district reference data is now available on the server."
echo "The ZIP files are kept as permanent references."
echo "The XLS files are extracted and ready for the parser."
echo "The JSON files contain data for all 219 districts."
"@

$tempScript = [System.IO.Path]::GetTempFileName()
$serverScript | Out-File -FilePath $tempScript -Encoding ASCII

Write-Host "`nExecuting server-side extraction and parsing..." -ForegroundColor Yellow
ssh "${SERVER_USER}@${SERVER_HOST}" "bash -s" < $tempScript

Remove-Item $tempScript

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✓ ALL DONE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your server now has:" -ForegroundColor Green
Write-Host "  - All 3 ZIP files (permanent references)" -ForegroundColor White
Write-Host "  - All extracted XLS files" -ForegroundColor White
Write-Host "  - All extracted PDF files" -ForegroundColor White
Write-Host "  - All extracted shapefiles" -ForegroundColor White
Write-Host "  - 6 parsed JSON files (219 districts)" -ForegroundColor White
Write-Host ""
Write-Host "Location: ${SERVER_PATH}" -ForegroundColor Yellow
