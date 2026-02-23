#!/bin/bash
# Script to configure environment variables on the Lightsail instance
# Run this script on the instance after deployment

set -e

echo "=== WhoVoted Environment Configuration ==="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Please run as ubuntu user (not root)"
    exit 1
fi

# Prompt for AWS credentials
echo "Enter your AWS credentials:"
read -p "AWS Access Key ID: " AWS_ACCESS_KEY
read -sp "AWS Secret Access Key: " AWS_SECRET_KEY
echo ""
read -p "AWS Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Generate a random secret key
SECRET_KEY=$(openssl rand -hex 32)

# Update .env file
echo "Updating environment configuration..."
cat > /opt/whovoted/.env << ENVEOF
# Flask Configuration
FLASK_APP=backend/app.py
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY

# AWS Configuration
AWS_REGION=$AWS_REGION
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_KEY

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin2026!
ENVEOF

# Secure the .env file
chmod 600 /opt/whovoted/.env

echo ""
echo "Environment configured successfully!"
echo ""
echo "Restarting application..."
sudo supervisorctl restart whovoted

echo ""
echo "Checking application status..."
sleep 3
sudo supervisorctl status whovoted

echo ""
echo "=== Configuration Complete! ==="
echo ""
echo "Your application should now be running."
echo "Check logs with: tail -f /opt/whovoted/logs/gunicorn-error.log"
echo ""
