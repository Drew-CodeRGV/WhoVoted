#!/bin/bash
# Deploy LLM timeout fix to production server

set -e  # Exit on error

echo "=========================================="
echo "Deploying LLM Timeout Fix"
echo "=========================================="
echo ""

# Navigate to project directory
cd /var/www/politiquera

# Pull latest code
echo "Step 1: Pulling latest code from GitHub..."
git pull origin main
echo "✓ Code updated"
echo ""

# Clear Python cache
echo "Step 2: Clearing Python cache..."
find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Cache cleared"
echo ""

# Restart gunicorn
echo "Step 3: Restarting gunicorn..."
pkill -9 -f "gunicorn.*app:app" || true
sleep 2

cd backend
source venv/bin/activate
nohup gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 --log-level info app:app > /var/www/politiquera/backend/logs/gunicorn.log 2>&1 &
echo "✓ Gunicorn restarted"
echo ""

# Wait for gunicorn to start
echo "Step 4: Waiting for gunicorn to start..."
sleep 5

# Check if gunicorn is running
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn is running"
else
    echo "✗ Gunicorn failed to start"
    echo "Check logs: tail -f /var/www/politiquera/backend/logs/gunicorn.log"
    exit 1
fi
echo ""

# Run tests
echo "Step 5: Running tests..."
cd /var/www/politiquera
python3 deploy/test_llm_http_complete.py
echo ""

# Test endpoint
echo "Step 6: Testing endpoint (expect 401 without auth)..."
response=$(curl -s -w "\n%{http_code}" -X POST https://politiquera.com/api/llm/query \
    -H "Content-Type: application/json" \
    -d '{"question": "Show me voters in TX-15"}')
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "401" ]; then
    echo "✓ Endpoint responding correctly (401 Unauthorized)"
else
    echo "⚠ Got HTTP $http_code (expected 401)"
fi
echo ""

echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Open https://politiquera.com in browser"
echo "2. Sign in with Google"
echo "3. Click the brain icon (🧠) to open AI search"
echo "4. Try query: 'Show me Female voters in TX-15 who voted in 2024 but not 2026'"
echo ""
echo "Monitor logs:"
echo "  tail -f /var/www/politiquera/backend/logs/gunicorn.log"
echo "  tail -f /var/www/politiquera/backend/logs/error.log"
