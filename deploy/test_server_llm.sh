#!/bin/bash
# Test LLM endpoint on production server

echo "=========================================="
echo "Testing LLM Endpoint on Production Server"
echo "=========================================="
echo ""

# Test 1: Check Ollama is running
echo "TEST 1: Ollama Status"
echo "----------------------------------------"
if command -v ollama &> /dev/null; then
    echo "✓ Ollama command found"
    ollama list
    echo ""
else
    echo "✗ Ollama not found in PATH"
    exit 1
fi

# Test 2: Check Python can import ollama
echo "TEST 2: Python Ollama Import"
echo "----------------------------------------"
cd /var/www/politiquera/backend
source venv/bin/activate
python3 -c "import ollama; print('✓ ollama module imported'); models = ollama.list(); print(f'Models: {[m[\"name\"] for m in models.get(\"models\", [])]}')"
echo ""

# Test 3: Direct Python test
echo "TEST 3: Direct Python LLM Test"
echo "----------------------------------------"
cd /var/www/politiquera
python3 deploy/test_llm_http_complete.py
echo ""

# Test 4: Check gunicorn is running
echo "TEST 4: Gunicorn Status"
echo "----------------------------------------"
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn is running"
    ps aux | grep gunicorn | grep -v grep
else
    echo "✗ Gunicorn is not running"
    exit 1
fi
echo ""

# Test 5: Test endpoint without auth (should get 401)
echo "TEST 5: Endpoint Without Auth (expect 401)"
echo "----------------------------------------"
response=$(curl -s -w "\n%{http_code}" -X POST https://politiquera.com/api/llm/query \
    -H "Content-Type: application/json" \
    -d '{"question": "Show me voters in TX-15"}')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "401" ]; then
    echo "✓ Got 401 Unauthorized (correct)"
else
    echo "✗ Got HTTP $http_code (expected 401)"
    echo "Response: $body"
fi
echo ""

# Test 6: Check logs for errors
echo "TEST 6: Recent Error Logs"
echo "----------------------------------------"
echo "Last 20 lines of error log:"
tail -n 20 /var/www/politiquera/backend/logs/error.log
echo ""

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "If all tests pass, the issue is likely:"
echo "1. Session/auth cookie not being sent from browser"
echo "2. Ollama hanging only when called from gunicorn worker"
echo "3. Worker timeout or thread blocking"
echo ""
echo "Next: Check browser console for cookie/auth issues"
