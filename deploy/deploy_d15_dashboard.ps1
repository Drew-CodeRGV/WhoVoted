# Deploy District 15 Dashboard to production (PowerShell version)

Write-Host "Deploying D15 Dashboard..." -ForegroundColor Cyan

# Copy dashboard files
Write-Host "Copying dashboard files..." -ForegroundColor Yellow
scp public/d15/index.html root@politiquera.com:/opt/whovoted/public/d15/
scp public/d15/dashboard.js root@politiquera.com:/opt/whovoted/public/d15/
scp public/d15/upload.html root@politiquera.com:/opt/whovoted/public/d15/

# Copy logo
Write-Host "Copying logo..." -ForegroundColor Yellow
scp public/assets/bobby-pulido-logo.png root@politiquera.com:/opt/whovoted/public/assets/

# Copy districts.json
Write-Host "Copying districts.json..." -ForegroundColor Yellow
scp public/data/districts.json root@politiquera.com:/opt/whovoted/public/data/

# Copy backend changes
Write-Host "Copying backend API updates..." -ForegroundColor Yellow
scp backend/app.py root@politiquera.com:/opt/whovoted/backend/

# Restart backend to pick up API changes
Write-Host "Restarting backend..." -ForegroundColor Yellow
ssh root@politiquera.com "systemctl restart whovoted"

Write-Host ""
Write-Host "✓ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard available at: https://politiquera.com/d15" -ForegroundColor Cyan
Write-Host "Upload interface at: https://politiquera.com/d15/upload.html" -ForegroundColor Cyan
