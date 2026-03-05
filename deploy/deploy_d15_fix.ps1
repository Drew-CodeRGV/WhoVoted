# Deploy D15 nginx fix to server

Write-Host "Deploying D15 fix script to server..." -ForegroundColor Cyan

# Copy the fix script to server
scp WhoVoted/deploy/fix_d15_nginx.sh root@politiquera.com:/opt/whovoted/deploy/

# Make it executable and run it
ssh root@politiquera.com "chmod +x /opt/whovoted/deploy/fix_d15_nginx.sh && bash /opt/whovoted/deploy/fix_d15_nginx.sh"

Write-Host "`nDone! Check the output above for any errors." -ForegroundColor Green
Write-Host "If successful, test at: https://politiquera.com/d15/" -ForegroundColor Yellow
