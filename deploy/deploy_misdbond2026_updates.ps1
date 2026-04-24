# Deploy McAllen ISD Bond 2026 updates to server

Write-Host "Deploying McAllen ISD Bond 2026 updates..." -ForegroundColor Cyan

# Upload HTML file
Write-Host "`nUploading index.html..." -ForegroundColor Yellow
scp -i whovoted-key.pem ../public/misdbond2026/index.html ubuntu@politiquera.com:/opt/whovoted/public/misdbond2026/

# Upload JS file
Write-Host "Uploading map.js..." -ForegroundColor Yellow
scp -i whovoted-key.pem ../public/misdbond2026/map.js ubuntu@politiquera.com:/opt/whovoted/public/misdbond2026/

Write-Host "`nFiles uploaded successfully!" -ForegroundColor Green
Write-Host "`nView at: https://politiquera.com/misdbond2026/" -ForegroundColor Cyan
