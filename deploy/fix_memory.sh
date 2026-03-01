#!/bin/bash
# Fix OOM issues on low-memory Lightsail instance

# 1. Add 1GB swap file if not already present
if [ ! -f /swapfile ]; then
    echo "Creating 1GB swap file..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap enabled"
else
    echo "Swap file already exists"
    sudo swapon /swapfile 2>/dev/null || true
fi

# 2. Reduce gunicorn workers from 5 to 2
GUNICORN_CONF="/opt/whovoted/gunicorn_config.py"
if [ -f "$GUNICORN_CONF" ]; then
    # Replace workers = N with workers = 2
    sudo sed -i 's/^workers\s*=\s*[0-9]*/workers = 2/' "$GUNICORN_CONF"
    echo "Reduced gunicorn workers to 2"
    grep workers "$GUNICORN_CONF"
else
    echo "Gunicorn config not found at $GUNICORN_CONF"
fi

# 3. Restart the service
sudo supervisorctl restart whovoted
echo "Service restarted"

# 4. Show memory status
echo "---"
free -m
echo "---"
swapon --show
