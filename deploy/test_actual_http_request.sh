#!/bin/bash
# Test the actual HTTP endpoint with a real request
# This simulates what the browser does

echo "=========================================="
echo "TESTING ACTUAL HTTP ENDPOINT"
echo "=========================================="

echo ""
echo "[1/2] Making HTTP POST request to /api/llm/query..."
echo "Query: 'Show me voters in TX-15 who voted in 2024 but not 2026'"
echo ""

# Make the request with a 30 second timeout
RESPONSE=$(curl -s -m 30 -X POST http://127.0.0.1:5000/api/llm/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me voters in TX-15 who voted in 2024 but not 2026","context":{}}' \
  2>&1)

EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo ""

if [ $EXIT_CODE -eq 28 ]; then
    echo "✗ REQUEST TIMED OUT (30 seconds)"
    echo "This means the LLM is hanging or taking too long"
    exit 1
elif [ $EXIT_CODE -ne 0 ]; then
    echo "✗ REQUEST FAILED with exit code $EXIT_CODE"
    exit 1
fi

echo "[2/2] Checking response..."
echo "Response (first 500 chars):"
echo "$RESPONSE" | head -c 500
echo ""
echo ""

# Check if response is JSON or HTML
if echo "$RESPONSE" | grep -q "^<"; then
    echo "✗ RESPONSE IS HTML (indicates 500 error)"
    echo "The endpoint is returning an error page instead of JSON"
    exit 1
elif echo "$RESPONSE" | grep -q "Unauthorized"; then
    echo "✓ Got 401 Unauthorized (expected without auth)"
    echo "This means the endpoint is working but requires authentication"
    exit 0
elif echo "$RESPONSE" | grep -q '"success"'; then
    echo "✓ GOT JSON RESPONSE"
    echo "The endpoint is working!"
    exit 0
else
    echo "? UNEXPECTED RESPONSE"
    exit 1
fi
