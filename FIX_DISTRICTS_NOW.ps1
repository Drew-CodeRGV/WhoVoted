# COMPLETE DISTRICT ASSIGNMENT FIX
# Run this script to fix everything in one go

Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host "DISTRICT ASSIGNMENT - COMPLETE FIX"
Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host ""

# Step 1: Find the statewide CSV
Write-Host "Step 1: Locate statewide CSV file"
Write-Host "Please provide the path to your STATEWIDE_VOTER_INFO.csv file:"
Write-Host "(The file with columns: id_voter, tx_precinct_code, tx_county_name, voting_method)"
Write-Host ""
$csvPath = Read-Host "CSV file path"

if (-not (Test-Path $csvPath)) {
    Write-Host "ERROR: File not found: $csvPath" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found CSV file: $csvPath" -ForegroundColor Green
$csvSize = (Get-Item $csvPath).Length / 1MB
Write-Host "  Size: $([math]::Round($csvSize, 1)) MB"
Write-Host ""

# Step 2: Upload CSV to server
Write-Host "Step 2: Uploading CSV to server..."
scp -i WhoVoted/deploy/whovoted-key.pem $csvPath ubuntu@politiquera.com:/opt/whovoted/data/STATEWIDE_VOTER_INFO.csv

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload CSV" -ForegroundColor Red
    exit 1
}

Write-Host "✓ CSV uploaded successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Upload backfill script
Write-Host "Step 3: Uploading backfill script..."
scp -i WhoVoted/deploy/whovoted-key.pem WhoVoted/deploy/backfill_precincts_from_statewide_csv.py ubuntu@politiquera.com:/opt/whovoted/deploy/

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload script" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Script uploaded" -ForegroundColor Green
Write-Host ""

# Step 4: Run backfill
Write-Host "Step 4: Backfilling precinct data..."
Write-Host "(This will update 62,876 records with missing precinct data)"
Write-Host ""
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 deploy/backfill_precincts_from_statewide_csv.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Backfill failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Precinct data backfilled" -ForegroundColor Green
Write-Host ""

# Step 5: Upload district assignment script
Write-Host "Step 5: Uploading district assignment script..."
scp -i WhoVoted/deploy/whovoted-key.pem WhoVoted/deploy/build_normalized_precinct_system.py ubuntu@politiquera.com:/opt/whovoted/deploy/

Write-Host "✓ Script uploaded" -ForegroundColor Green
Write-Host ""

# Step 6: Run district assignment
Write-Host "Step 6: Assigning districts..."
Write-Host "(This will match precincts to districts for all voters)"
Write-Host ""
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 deploy/build_normalized_precinct_system.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: District assignment failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Districts assigned" -ForegroundColor Green
Write-Host ""

# Step 7: Verify results
Write-Host "Step 7: Verifying results..."
scp -i WhoVoted/deploy/whovoted-key.pem WhoVoted/deploy/final_district_assignment_status.py ubuntu@politiquera.com:/opt/whovoted/deploy/
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 deploy/final_district_assignment_status.py"

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host "COMPLETE!" -ForegroundColor Green
Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review the verification results above"
Write-Host "2. If D15 accuracy is 95%+, regenerate district caches"
Write-Host "3. Deploy to production"
Write-Host ""
