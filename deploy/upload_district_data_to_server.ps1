# Upload district reference data to server and extract
# PowerShell script for Windows

# Configuration - UPDATE THESE VALUES
$SERVER_USER = "your_username"
$SERVER_HOST = "your_server_ip"
$SERVER_PATH = "/home/ubuntu/WhoVoted/data/district_reference"

Write-Host "========================================" -ForegroundColor Green
Write-Host "District Data Upload Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "data/district_reference")) {
    Write-Host "Error: Must run from WhoVoted directory" -ForegroundColor Red
    exit 1
}

Set-Location data/district_reference

# Check for ZIP files
Write-Host "`nChecking for ZIP files..." -ForegroundColor Yellow
$zipFiles = Get-ChildItem -Filter "*.zip" -ErrorAction SilentlyContinue

if ($zipFiles.Count -eq 0) {
    Write-Host "No ZIP files found in data/district_reference/" -ForegroundColor Red
    Write-Host "Looking for:" -ForegroundColor Yellow
    Write-Host "  - PLANC2333_All_Files_*.zip (Congressional)"
    Write-Host "  - PLANS2168_All_Files_*.zip (State Senate)"
    Write-Host "  - PLANH2316_All_Files_*.zip (State House)"
    exit 1
}

Write-Host "Found $($zipFiles.Count) ZIP file(s)" -ForegroundColor Green
$zipFiles | ForEach-Object { Write-Host "  - $($_.Name) ($([math]::Round($_.Length/1MB, 2)) MB)" }

# Create remote directory
Write-Host "`nCreating remote directory..." -ForegroundColor Yellow
ssh "${SERVER_USER}@${SERVER_HOST}" "mkdir -p ${SERVER_PATH}"

# Upload ZIP files
Write-Host "`nUploading ZIP files to server..." -ForegroundColor Yellow
foreach ($zipFile in $zipFiles) {
    Write-Host "Uploading: $($zipFile.Name)" -ForegroundColor Green
    scp $zipFile.FullName "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Uploaded: $($zipFile.Name)" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to upload: $($zipFile.Name)" -ForegroundColor Red
        exit 1
    }
}

# Extract on server
Write-Host "`nExtracting files on server..." -ForegroundColor Yellow
$extractScript = @"
cd ${SERVER_PATH}

echo 'Extracting ZIP files...'
for zipfile in *.zip; do
    if [ -f "`$zipfile" ]; then
        echo "Extracting: `$zipfile"
        unzip -o "`$zipfile"
        echo "✓ Extracted: `$zipfile"
    fi
done

echo ""
echo "Listing XLS files:"
ls -lh *.xls | head -20

echo ""
echo "Total XLS files:"
ls -1 *.xls | wc -l
"@

ssh "${SERVER_USER}@${SERVER_HOST}" $extractScript

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Upload Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nNext steps:"
Write-Host "1. SSH to server: " -NoNewline
Write-Host "ssh ${SERVER_USER}@${SERVER_HOST}" -ForegroundColor Yellow
Write-Host "2. Run parser: " -NoNewline
Write-Host "cd /home/ubuntu/WhoVoted && python deploy/parse_district_files.py" -ForegroundColor Yellow
