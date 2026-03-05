# Quick deployment script for Windows
# Run this to deploy everything to the server

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYING ELECTION DAY SCRAPER TO SERVER" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Pull latest code on server
Write-Host "Step 1: Pulling latest code..." -ForegroundColor Yellow
ssh root@politiquera.com "cd /opt/whovoted && git pull"

# Make scripts executable
Write-Host "`nStep 2: Making scripts executable..." -ForegroundColor Yellow
ssh root@politiquera.com "cd /opt/whovoted && chmod +x deploy/*.sh"

# Run the import
Write-Host "`nStep 3: Running election day import..." -ForegroundColor Yellow
Write-Host "This will take 5-10 minutes. Please wait..." -ForegroundColor Yellow
ssh root@politiquera.com "cd /opt/whovoted && bash deploy/import_election_day_only.sh"

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Check the website: https://politiquera.com/" -ForegroundColor Cyan
