#!/bin/bash
# Quick deployment script for Linux/Mac
# Run this to deploy everything to the server

echo "================================================================================"
echo "DEPLOYING ELECTION DAY SCRAPER TO SERVER"
echo "================================================================================"
echo ""

# Pull latest code on server
echo "Step 1: Pulling latest code..."
ssh root@politiquera.com "cd /opt/whovoted && git pull"

# Make scripts executable
echo ""
echo "Step 2: Making scripts executable..."
ssh root@politiquera.com "cd /opt/whovoted && chmod +x deploy/*.sh"

# Run the import
echo ""
echo "Step 3: Running election day import..."
echo "This will take 5-10 minutes. Please wait..."
ssh root@politiquera.com "cd /opt/whovoted && bash deploy/import_election_day_only.sh"

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""
echo "Check the website: https://politiquera.com/"
