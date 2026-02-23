#!/bin/bash
# Enable HTTPS for politiquera.com using Let's Encrypt
# Run this script on your Lightsail instance

set -e

echo "=== Enabling HTTPS for politiquera.com ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Configuration
DOMAIN="politiquera.com"
EMAIL="your-email@example.com"  # Change this to your email

echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Prompt for email if not changed
if [ "$EMAIL" = "your-email@example.com" ]; then
    read -p "Enter your email address for Let's Encrypt notifications: " EMAIL
fi

echo ""
echo "Step 1: Installing Certbot..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

echo ""
echo "Step 2: Backing up current Nginx configuration..."
cp /etc/nginx/sites-available/whovoted /etc/nginx/sites-available/whovoted.backup

echo ""
echo "Step 3: Updating Nginx configuration for $DOMAIN..."

# Create new Nginx configuration with domain name
cat > /etc/nginx/sites-available/whovoted << 'EOF'
server {
    listen 80;
    server_name politiquera.com www.politiquera.com;

    # Root directory for static files
    root /opt/whovoted/public;
    index index.html;

    # Increase client body size for file uploads (100MB)
    client_max_body_size 100M;

    # Main application
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

    # Admin routes
    location /admin {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Static files
    location /data {
        alias /opt/whovoted/data;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    location /assets {
        alias /opt/whovoted/public/assets;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
EOF

echo ""
echo "Step 4: Testing Nginx configuration..."
nginx -t

echo ""
echo "Step 5: Reloading Nginx..."
systemctl reload nginx

echo ""
echo "Step 6: Opening port 443 (HTTPS) in Lightsail firewall..."
echo "You need to run this command from your local machine:"
echo ""
echo "aws lightsail open-instance-public-ports --instance-name whovoted-app --port-info fromPort=443,toPort=443,protocol=tcp --region us-east-1"
echo ""
read -p "Press Enter after you've opened port 443 in Lightsail..."

echo ""
echo "Step 7: Obtaining SSL certificate from Let's Encrypt..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

echo ""
echo "Step 8: Testing SSL certificate renewal..."
certbot renew --dry-run

echo ""
echo "=== HTTPS Setup Complete! ==="
echo ""
echo "Your site is now available at:"
echo "  https://politiquera.com"
echo "  https://www.politiquera.com"
echo ""
echo "HTTP traffic will automatically redirect to HTTPS."
echo ""
echo "SSL certificate will auto-renew via cron job."
echo "Certificate expires in 90 days and will renew automatically."
echo ""
echo "To manually renew the certificate:"
echo "  sudo certbot renew"
echo ""
echo "To check certificate status:"
echo "  sudo certbot certificates"
echo ""
