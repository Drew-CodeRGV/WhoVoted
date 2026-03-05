#!/bin/bash
# Single command to deploy LLM fix to production
# Run this script from your local machine where you have SSH access

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYING LLM FIX TO PRODUCTION                         ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Execute deployment on server
ssh root@politiquera.com << 'ENDSSH'
cd /var/www/politiquera

echo "Step 1: Pulling latest code..."
git pull origin main

echo ""
echo "Step 2: Clearing Python cache..."
find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "Step 3: Restarting gunicorn..."
pkill -9 -f "gunicorn.*app:app" || true
sleep 3

cd backend
source venv/bin/activate
nohup gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 --log-level info app:app > logs/gunicorn.log 2>&1 &

echo ""
echo "Step 4: Waiting for gunicorn to start..."
sleep 5

if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn is running"
else
    echo "✗ Gunicorn failed to start"
    exit 1
fi

echo ""
echo "Step 5: Testing endpoint..."
response=$(curl -s -w "\n%{http_code}" -X POST https://politiquera.com/api/llm/query \
    -H "Content-Type: application/json" \
    -d '{"question": "Show me voters in TX-15"}' \
    --max-time 10)

http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "401" ]; then
    echo "✓ Endpoint responding correctly (401 Unauthorized)"
else
    echo "⚠ Got HTTP $http_code"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                        DEPLOYMENT COMPLETE!                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Test in browser:"
echo "1. Go to https://politiquera.com"
echo "2. Sign in with Google"
echo "3. Click brain icon (🧠)"
echo "4. Try: 'Show me Female voters in TX-15 who voted in 2024 but not 2026'"
echo ""

ENDSSH

echo "✓ Deployment script completed successfully"
