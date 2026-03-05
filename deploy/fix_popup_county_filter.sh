#!/bin/bash
# Deploy popup county filter fix to production server

echo "=== Deploying Popup County Filter Fix ==="
echo "This fixes voter popups not loading data when a specific county is selected"
echo ""

# Pull latest code
echo "1. Pulling latest code from GitHub..."
cd /opt/whovoted
git pull origin main

# Clear Python cache
echo "2. Clearing Python cache..."
rm -rf backend/__pycache__

# Restart gunicorn
echo "3. Restarting gunicorn..."
sudo pkill -9 gunicorn
cd /opt/whovoted
source venv/bin/activate
PYTHONDONTWRITEBYTECODE=1 nohup gunicorn -c gunicorn_config.py -b 127.0.0.1:5000 backend.app:app > logs/gunicorn.log 2>&1 &

echo ""
echo "=== Deployment Complete ==="
echo "Changes:"
echo "  - Frontend: Added county parameter to /api/voters/at API calls"
echo "  - Backend: Updated endpoint to accept and filter by county"
echo "  - Database: Updated get_voters_at_location() to filter by county list"
echo ""
echo "Test by:"
echo "  1. Select a specific county (e.g., Brooks)"
echo "  2. Click on a voter marker"
echo "  3. Popup should now load voter details correctly"
echo ""
