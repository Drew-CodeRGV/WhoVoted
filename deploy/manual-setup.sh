#!/bin/bash
# Manual setup script for WhoVoted on Lightsail
# Run this if the automatic setup fails

set -e

echo "=== WhoVoted Manual Setup ==="
cd /opt/whovoted

# Try shallow clone first (faster, less data)
echo "Attempting shallow clone..."
if ! git clone --depth 1 https://github.com/Drew-CodeRGV/WhoVoted.git .; then
    echo "Shallow clone failed, trying with increased buffer..."
    git config --global http.postBuffer 524288000
    git clone https://github.com/Drew-CodeRGV/WhoVoted.git .
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install gunicorn

# Create necessary directories
echo "Creating application directories..."
mkdir -p data logs uploads public/data backend/admin

# Set permissions
echo "Setting permissions..."
chmod -R 755 /opt/whovoted
chmod -R 777 /opt/whovoted/data
chmod -R 777 /opt/whovoted/logs
chmod -R 777 /opt/whovoted/uploads

# Create environment file
echo "Creating environment configuration..."
cat > /opt/whovoted/.env << 'ENVEOF'
# Flask Configuration
FLASK_APP=backend/app.py
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-this

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin2026!
ENVEOF

# Create Gunicorn configuration
echo "Creating Gunicorn configuration..."
cat > /opt/whovoted/gunicorn_config.py << 'GUNICORNEOF'
import multiprocessing

bind = "127.0.0.1:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 2
errorlog = "/opt/whovoted/logs/gunicorn-error.log"
accesslog = "/opt/whovoted/logs/gunicorn-access.log"
loglevel = "info"
GUNICORNEOF

# Create Supervisor configuration
echo "Creating Supervisor configuration..."
sudo tee /etc/supervisor/conf.d/whovoted.conf > /dev/null << 'SUPERVISOREOF'
[program:whovoted]
directory=/opt/whovoted/backend
command=/opt/whovoted/venv/bin/gunicorn -c /opt/whovoted/gunicorn_config.py -b 127.0.0.1:5000 app:app
user=ubuntu
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/opt/whovoted/logs/supervisor-error.log
stdout_logfile=/opt/whovoted/logs/supervisor-output.log
environment=PATH="/opt/whovoted/venv/bin"
SUPERVISOREOF

# Create Nginx configuration
echo "Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/whovoted > /dev/null << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /static {
        alias /opt/whovoted/public;
        expires 30d;
    }
}
NGINXEOF

# Enable Nginx site
echo "Configuring Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/whovoted /etc/nginx/sites-enabled/
sudo nginx -t

# Reload services
echo "Starting services..."
sudo supervisorctl reread
sudo supervisorctl update
sudo systemctl restart nginx
sudo systemctl enable supervisor

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit /opt/whovoted/.env with your AWS credentials"
echo "2. Run: sudo supervisorctl restart whovoted"
echo "3. Check status: sudo supervisorctl status whovoted"
echo ""
