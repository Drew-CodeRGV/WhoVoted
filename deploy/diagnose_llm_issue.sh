#!/bin/bash
# Comprehensive diagnostic script for LLM issues
# Run this if problems persist after deployment

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                      LLM ISSUE DIAGNOSTIC TOOL                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# System Information
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ System Information                                                         │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

echo "Hostname: $(hostname)"
echo "OS: $(uname -a)"
echo "Python: $(python3 --version)"
echo "Disk space:"
df -h /var/www/politiquera
echo ""

# ============================================================================
# Ollama Status
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Ollama Status                                                              │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

if command -v ollama &> /dev/null; then
    echo "✓ Ollama command found: $(which ollama)"
    echo ""
    
    echo "Testing ollama list (should be < 1 second)..."
    time_start=$(date +%s.%N)
    ollama list
    time_end=$(date +%s.%N)
    time_diff=$(echo "$time_end - $time_start" | bc)
    echo "Time: ${time_diff}s"
    
    if (( $(echo "$time_diff > 2" | bc -l) )); then
        echo "⚠ WARNING: ollama list is slow (> 2 seconds)"
    else
        echo "✓ ollama list is responsive"
    fi
    echo ""
    
    echo "Testing simple generation (should be < 10 seconds)..."
    time_start=$(date +%s.%N)
    ollama run llama3.2:latest "Say hello" --verbose 2>&1 | head -n 5
    time_end=$(date +%s.%N)
    time_diff=$(echo "$time_end - $time_start" | bc)
    echo "Time: ${time_diff}s"
    
    if (( $(echo "$time_diff > 15" | bc -l) )); then
        echo "⚠ WARNING: Ollama generation is slow (> 15 seconds)"
    else
        echo "✓ Ollama generation is responsive"
    fi
else
    echo "✗ Ollama command not found"
fi
echo ""

# ============================================================================
# Python Ollama Module
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Python Ollama Module                                                       │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

cd /var/www/politiquera/backend
source venv/bin/activate

python3 << 'EOF'
import sys
import time

try:
    import ollama
    print("✓ ollama module imported")
    
    # Test list
    print("\nTesting ollama.list()...")
    start = time.time()
    models = ollama.list()
    elapsed = time.time() - start
    print(f"Time: {elapsed:.2f}s")
    
    available = [m['name'] for m in models.get('models', [])]
    print(f"Available models: {available}")
    
    if elapsed > 2:
        print("⚠ WARNING: ollama.list() is slow")
    else:
        print("✓ ollama.list() is responsive")
    
    # Test generation
    print("\nTesting ollama.generate()...")
    start = time.time()
    response = ollama.generate(
        model='llama3.2:latest',
        prompt='Say "Hello" and nothing else.',
        options={'num_predict': 10}
    )
    elapsed = time.time() - start
    print(f"Time: {elapsed:.2f}s")
    print(f"Response: {response['response'][:50]}")
    
    if elapsed > 10:
        print("⚠ WARNING: ollama.generate() is slow")
    else:
        print("✓ ollama.generate() is responsive")
    
except ImportError as e:
    print(f"✗ Failed to import ollama: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error testing ollama: {e}")
    sys.exit(1)
EOF

echo ""

# ============================================================================
# Gunicorn Status
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Gunicorn Status                                                            │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn is running"
    echo ""
    echo "Processes:"
    ps aux | grep gunicorn | grep -v grep
    echo ""
    
    echo "Worker count:"
    pgrep -f "gunicorn.*app:app" | wc -l
else
    echo "✗ Gunicorn is not running"
fi
echo ""

# ============================================================================
# Recent Logs
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Recent Error Logs (last 30 lines)                                         │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

if [ -f /var/www/politiquera/backend/logs/error.log ]; then
    tail -n 30 /var/www/politiquera/backend/logs/error.log
else
    echo "No error log found"
fi
echo ""

# ============================================================================
# LLM-Specific Logs
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ LLM-Related Logs (last 20 matches)                                        │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

if [ -f /var/www/politiquera/backend/logs/error.log ]; then
    grep -i "llm\|ollama\|timeout" /var/www/politiquera/backend/logs/error.log | tail -n 20
else
    echo "No error log found"
fi
echo ""

# ============================================================================
# Network Test
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Network Test (localhost)                                                  │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

echo "Testing connection to gunicorn (127.0.0.1:5000)..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/ > /dev/null 2>&1; then
    echo "✓ Gunicorn is accessible on localhost"
else
    echo "✗ Cannot connect to gunicorn on localhost"
fi
echo ""

# ============================================================================
# Resource Usage
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Resource Usage                                                             │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

echo "Memory:"
free -h
echo ""

echo "CPU Load:"
uptime
echo ""

echo "Top processes by CPU:"
ps aux --sort=-%cpu | head -n 10
echo ""

echo "Top processes by Memory:"
ps aux --sort=-%mem | head -n 10
echo ""

# ============================================================================
# Code Version
# ============================================================================
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Code Version                                                               │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

cd /var/www/politiquera
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log -1 --oneline)"
echo "Last pull: $(stat -c %y .git/FETCH_HEAD 2>/dev/null || echo 'Unknown')"
echo ""

echo "Checking for threading timeout in llm_query.py..."
if grep -q "run_with_timeout" backend/llm_query.py; then
    echo "✓ Threading timeout code found"
else
    echo "✗ Threading timeout code NOT found (old version?)"
fi
echo ""

# ============================================================================
# Recommendations
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                              RECOMMENDATIONS                               ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check for slow Ollama
if command -v ollama &> /dev/null; then
    time_start=$(date +%s.%N)
    ollama list > /dev/null 2>&1
    time_end=$(date +%s.%N)
    time_diff=$(echo "$time_end - $time_start" | bc)
    
    if (( $(echo "$time_diff > 2" | bc -l) )); then
        echo "⚠ Ollama is slow. Consider:"
        echo "  • Restarting Ollama service"
        echo "  • Using a smaller model (llama3.2:1b)"
        echo "  • Checking system resources"
        echo ""
    fi
fi

# Check for old code
if ! grep -q "run_with_timeout" /var/www/politiquera/backend/llm_query.py; then
    echo "⚠ Code appears to be old version. Run:"
    echo "  cd /var/www/politiquera"
    echo "  git pull origin main"
    echo "  bash deploy/complete_llm_fix.sh"
    echo ""
fi

# Check gunicorn
if ! pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "⚠ Gunicorn is not running. Start with:"
    echo "  cd /var/www/politiquera/backend"
    echo "  source venv/bin/activate"
    echo "  nohup gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 app:app > logs/gunicorn.log 2>&1 &"
    echo ""
fi

echo "Diagnostic complete!"
echo ""
