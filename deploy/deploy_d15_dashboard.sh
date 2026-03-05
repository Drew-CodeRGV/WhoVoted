#!/bin/bash
# Deploy District 15 Dashboard to production

echo "Deploying D15 Dashboard..."

# Copy dashboard files
echo "Copying dashboard files..."
scp WhoVoted/public/d15/index.html root@politiquera.com:/opt/whovoted/public/d15/
scp WhoVoted/public/d15/dashboard.js root@politiquera.com:/opt/whovoted/public/d15/
scp WhoVoted/public/d15/upload.html root@politiquera.com:/opt/whovoted/public/d15/

# Copy logo
echo "Copying logo..."
scp WhoVoted/public/assets/bobby-pulido-logo.png root@politiquera.com:/opt/whovoted/public/assets/

# Copy districts.json
echo "Copying districts.json..."
scp WhoVoted/public/data/districts.json root@politiquera.com:/opt/whovoted/public/data/

# Restart backend to pick up API changes
echo "Restarting backend..."
ssh root@politiquera.com "systemctl restart whovoted"

echo "✓ Deployment complete!"
echo ""
echo "Dashboard available at: https://politiquera.com/d15"
echo "Upload interface at: https://politiquera.com/d15/upload.html"
