#!/bin/bash
# Setup LLM Query Assistant on production server

set -e

echo "=========================================="
echo "LLM Query Assistant Setup"
echo "=========================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# 1. Install Ollama
echo ""
echo "Step 1: Installing Ollama..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama already installed"
else
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
fi

# 2. Start Ollama service
echo ""
echo "Step 2: Starting Ollama service..."
systemctl enable ollama
systemctl start ollama
sleep 3
echo "✓ Ollama service started"

# 3. Pull Llama 3.2 model
echo ""
echo "Step 3: Pulling Llama 3.2 3B model (this may take a few minutes)..."
sudo -u ubuntu ollama pull llama3.2:3b-instruct
echo "✓ Model downloaded"

# 4. Install Python package
echo ""
echo "Step 4: Installing Python ollama package..."
/opt/whovoted/venv/bin/pip install ollama
echo "✓ Python package installed"

# 5. Test Ollama connection
echo ""
echo "Step 5: Testing Ollama connection..."
if curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
    echo "✓ Ollama is working correctly"
else
    echo "⚠ Warning: Ollama may not be responding correctly"
fi

# 6. Restart gunicorn to load new code
echo ""
echo "Step 6: Restarting gunicorn..."
pkill gunicorn || true
sleep 2
cd /opt/whovoted
PYTHONPATH=/opt/whovoted/backend /opt/whovoted/venv/bin/gunicorn -w 5 -b 127.0.0.1:5000 'app:app' --daemon
sleep 2
echo "✓ Gunicorn restarted"

# 7. Verify gunicorn is running
if pgrep -f gunicorn > /dev/null; then
    echo "✓ Gunicorn is running"
else
    echo "⚠ Warning: Gunicorn may not have started correctly"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "The AI-powered search is now available."
echo "Users can click the brain icon (🧠) to search."
echo ""
echo "Model: Llama 3.2 3B Instruct"
echo "Cost: $0/month (runs locally)"
echo "Memory: ~2GB RAM"
echo ""
echo "To check Ollama status: systemctl status ollama"
echo "To check available models: ollama list"
echo "To view logs: journalctl -u ollama -f"
echo ""
