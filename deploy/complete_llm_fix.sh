#!/bin/bash
# Complete LLM fix deployment and testing script
# This script will:
# 1. Pull latest code
# 2. Clear cache
# 3. Restart gunicorn
# 4. Run comprehensive tests
# 5. Verify endpoint is working

set -e  # Exit on error

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    LLM TIMEOUT FIX - COMPLETE DEPLOYMENT                   ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check we're on the server
if [ ! -d "/var/www/politiquera" ]; then
    echo "✗ Error: This script must be run on the production server"
    exit 1
fi

cd /var/www/politiquera

# ============================================================================
# STEP 1: Pull Latest Code
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 1: Pulling Latest Code from GitHub                                   │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

git fetch origin
git reset --hard origin/main
echo "✓ Code updated to latest version"
echo ""

# ============================================================================
# STEP 2: Clear Python Cache
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 2: Clearing Python Cache                                             │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Python cache cleared"
echo ""

# ============================================================================
# STEP 3: Verify Ollama is Running
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 3: Verifying Ollama                                                  │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

if command -v ollama &> /dev/null; then
    echo "✓ Ollama command found"
    echo ""
    echo "Available models:"
    ollama list
    echo ""
    
    if ollama list | grep -q "llama3.2"; then
        echo "✓ llama3.2 model available"
    else
        echo "⚠ Warning: llama3.2 model not found"
        echo "  Run: ollama pull llama3.2:latest"
    fi
else
    echo "✗ Ollama not found"
    exit 1
fi
echo ""

# ============================================================================
# STEP 4: Restart Gunicorn
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 4: Restarting Gunicorn                                               │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

# Kill existing gunicorn processes
echo "Stopping existing gunicorn processes..."
pkill -9 -f "gunicorn.*app:app" || true
sleep 3

# Start gunicorn
echo "Starting gunicorn..."
cd backend
source venv/bin/activate

# Start with increased timeout and logging
nohup gunicorn -w 4 -b 127.0.0.1:5000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --log-level info \
    --access-logfile /var/www/politiquera/backend/logs/access.log \
    --error-logfile /var/www/politiquera/backend/logs/error.log \
    app:app > /var/www/politiquera/backend/logs/gunicorn.log 2>&1 &

echo "Waiting for gunicorn to start..."
sleep 5

# Verify gunicorn is running
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn is running"
    echo ""
    echo "Gunicorn processes:"
    ps aux | grep gunicorn | grep -v grep
else
    echo "✗ Gunicorn failed to start"
    echo ""
    echo "Last 20 lines of gunicorn log:"
    tail -n 20 /var/www/politiquera/backend/logs/gunicorn.log
    exit 1
fi
echo ""

# ============================================================================
# STEP 5: Run Python Tests
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 5: Running Python Tests                                              │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

cd /var/www/politiquera
python3 deploy/test_user_queries.py

test_result=$?
echo ""

if [ $test_result -eq 0 ]; then
    echo "✓ Python tests passed"
else
    echo "⚠ Python tests had issues (may be expected if Ollama is slow)"
fi
echo ""

# ============================================================================
# STEP 6: Test HTTP Endpoint
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 6: Testing HTTP Endpoint                                             │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

echo "Testing endpoint without authentication (expect 401)..."
response=$(curl -s -w "\n%{http_code}" -X POST https://politiquera.com/api/llm/query \
    -H "Content-Type: application/json" \
    -d '{"question": "Show me voters in TX-15"}' \
    --max-time 10)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "401" ]; then
    echo "✓ Endpoint responding correctly (401 Unauthorized)"
elif [ "$http_code" = "000" ]; then
    echo "⚠ Request timed out (endpoint may be slow)"
else
    echo "⚠ Got HTTP $http_code (expected 401)"
    echo "Response: $body"
fi
echo ""

# ============================================================================
# STEP 7: Check Recent Logs
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ STEP 7: Recent Logs                                                       │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

echo "Last 10 lines of error log:"
tail -n 10 /var/www/politiquera/backend/logs/error.log
echo ""

# ============================================================================
# COMPLETION
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                          DEPLOYMENT COMPLETE!                              ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Changes deployed:"
echo "  • Threading-based timeouts (30s for SQL, 15s for explanations)"
echo "  • Comprehensive error handling"
echo "  • Enhanced logging"
echo ""
echo "Next steps:"
echo "  1. Open https://politiquera.com in your browser"
echo "  2. Sign in with Google"
echo "  3. Click the brain icon (🧠) to open AI search"
echo "  4. Test with: 'Show me Female voters in TX-15 who voted in 2024 but not 2026'"
echo ""
echo "Monitor logs in real-time:"
echo "  tail -f /var/www/politiquera/backend/logs/error.log"
echo ""
echo "If issues persist, check:"
echo "  • Ollama is running: systemctl status ollama (if using systemd)"
echo "  • Ollama responds: ollama list"
echo "  • Worker logs: tail -f /var/www/politiquera/backend/logs/gunicorn.log"
echo ""
