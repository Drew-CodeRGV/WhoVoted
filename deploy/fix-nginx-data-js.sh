#!/bin/bash
# Fix Nginx configuration to properly serve data.js and other JS files

set -e

echo "=== Fixing Nginx Configuration ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Step 1: Backing up current configuration..."
cp /etc/nginx/sites-available/whovoted /etc/nginx/sites-available/whovoted.backup.$(date +%Y%m%d_%H%M%S)

echo ""
echo "Step 2: Updating Nginx configuration..."
echo "The issue: /data location was matching /data.js"
echo "The fix: Change /data to /data/ (with trailing slash)"

# Update the configuration
cat > /etc/nginx/sites-available/whovoted << 'EOF'
server {
    server_name politiquera.com www.politiquera.com;

    # Root directory for static files
    root /opt/whovoted/public;
    index index.html;

    # Increase client body size for file uploads (100MB)
    client_max_body_size 100M;

    # Static files - MUST come before the main location block
    # Use trailing slash to avoid conflicts with data.js
    location /data/ {
        alias /opt/whovoted/data/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    location /assets {
        alias /opt/whovoted/public/assets;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Admin routes - proxy to Flask
    location /admin {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Main application - serve static files first, then proxy to Flask
    location / {
        try_files $uri $uri/ @app;
    }

    # Proxy to Flask application
    location @app {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/politiquera.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/politiquera.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = www.politiquera.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    if ($host = politiquera.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name politiquera.com www.politiquera.com;
    return 404; # managed by Certbot
}
EOF

echo ""
echo "Step 3: Testing Nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    echo "ERROR: Nginx configuration test failed!"
    echo "Restoring backup..."
    cp /etc/nginx/sites-available/whovoted.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-available/whovoted
    exit 1
fi

echo ""
echo "Step 4: Reloading Nginx..."
systemctl reload nginx

echo ""
echo "Step 5: Testing data.js access..."
sleep 2
curl -I https://politiquera.com/data.js 2>&1 | head -1

echo ""
echo "=== Fix Complete! ==="
echo ""
echo "The issue was that the Nginx location block:"
echo "  location /data {"
echo ""
echo "Was matching URLs like /data.js, causing Nginx to look in the wrong directory."
echo ""
echo "Changed to:"
echo "  location /data/ {"
echo ""
echo "Now /data.js will be served from /opt/whovoted/public/data.js"
echo "And /data/ URLs will be served from /opt/whovoted/data/"
echo ""
echo "Test your site: https://politiquera.com"
echo ""
