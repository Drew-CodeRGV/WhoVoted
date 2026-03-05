#!/bin/bash
# Complete deployment script with verification
# This should ALWAYS be used for deployments

set -e

echo "=========================================="
echo "DEPLOYMENT WITH VERIFICATION"
echo "=========================================="

# Step 1: Pull latest code
echo "[1/6] Pulling latest code from GitHub..."
cd /opt/whovoted
sudo git pull origin main

# Step 2: Clear Python cache
echo "[2/6] Clearing Python cache..."
cd /opt/whovoted/backend
sudo find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
sudo find . -name '*.pyc' -delete 2>/dev/null || true
echo "✓ Cache cleared"

# Step 3: Stop gunicorn
echo "[3/6] Stopping gunicorn..."
sudo pkill -9 -f 'gunicorn.*app:app' || true
sleep 2
echo "✓ Gunicorn stopped"

# Step 4: Start gunicorn
echo "[4/6] Starting gunicorn..."
cd /opt/whovoted/backend
sudo /opt/whovoted/venv/bin/gunicorn -w 6 -b 127.0.0.1:5000 app:app --daemon
sleep 3

# Step 5: Verify gunicorn is running
echo "[5/6] Verifying gunicorn..."
PROCESS_COUNT=$(ps aux | grep gunicorn | grep -v grep | wc -l)
if [ "$PROCESS_COUNT" -eq 7 ]; then
    echo "✓ Gunicorn running with 7 processes"
else
    echo "✗ ERROR: Expected 7 processes, found $PROCESS_COUNT"
    exit 1
fi

# Step 6: Test the LLM endpoint
echo "[6/6] Testing LLM functionality..."
cd /opt/whovoted
sudo /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/diagnose_and_fix_llm.py > /tmp/llm_test.log 2>&1
if grep -q "ALL TESTS PASSED" /tmp/llm_test.log; then
    echo "✓ LLM tests passed"
else
    echo "✗ LLM tests failed. Check /tmp/llm_test.log"
    tail -20 /tmp/llm_test.log
    exit 1
fi

echo ""
echo "=========================================="
echo "✓✓✓ DEPLOYMENT SUCCESSFUL ✓✓✓"
echo "=========================================="
echo "System is ready at https://politiquera.com"
