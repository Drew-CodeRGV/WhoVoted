# Quick Fix for WhoVoted Deployment

The current instance (3.219.219.82) is having issues. Here's how to fix it:

## Option 1: Delete and Recreate (Recommended)

The instance has configuration issues. It's faster to start fresh:

```powershell
# Delete the problematic instance
aws lightsail delete-instance --instance-name whovoted-app --region us-east-1

# Wait 30 seconds
Start-Sleep -Seconds 30

# Run the deployment script again
cd WhoVoted/deploy
.\deploy-to-lightsail.ps1
```

## Option 2: Try to Fix Current Instance

If you can eventually connect via SSH, here's the fix:

```bash
# SSH from WhoVoted/deploy directory
ssh -i whovoted-key.pem ubuntu@3.219.219.82

# Once connected, fix the Supervisor config
sudo tee /etc/supervisor/conf.d/whovoted.conf > /dev/null << 'EOF'
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
EOF

# Reload and start
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start whovoted

# Configure AWS credentials
cd /opt/whovoted/deploy
chmod +x configure-env.sh
./configure-env.sh
```

## Why the Issue Happened

The Flask app uses relative imports (`from config import...`) which requires running from the backend directory. The initial configuration tried to run from the root directory, causing import errors.

## Alternative: Use Render or PythonAnywhere

If Lightsail continues to have issues, consider these alternatives:

### Render (Easiest)
1. Go to render.com
2. Connect your GitHub repo
3. Create a new Web Service
4. Set build command: `pip install -r backend/requirements.txt`
5. Set start command: `cd backend && gunicorn app:app`
6. Add environment variables for AWS credentials
7. Deploy (free tier available)

### PythonAnywhere
1. Go to pythonanywhere.com
2. Create free account
3. Upload your code
4. Configure WSGI file
5. Set environment variables
6. Start web app

Both are simpler than Lightsail for Python web apps.
