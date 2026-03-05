#!/bin/bash
cd /opt/whovoted
source venv/bin/activate

# Clear cache using Python
python3 << 'EOF'
import sys
sys.path.insert(0, '/opt/whovoted')
from backend.app import cache_clear
cache_clear('elections:Hidalgo')
print("✓ Cache cleared for elections:Hidalgo")
EOF

# Test the API endpoint
echo ""
echo "Testing /api/elections?county=Hidalgo endpoint:"
curl -s "http://127.0.0.1:5000/api/elections?county=Hidalgo" | python3 -m json.tool | head -100
