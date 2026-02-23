# URGENT: Instance Too Small

## Problem

The current Lightsail instance (nano_3_0) only has 512MB RAM, which is insufficient for your application with the large geocoding cache files (77,650+ addresses = ~25MB JSON files).

The app is being killed by Out Of Memory (OOM) errors when trying to start.

## Solution: Upgrade Instance Size

You need at least the $10/month instance (micro_3_0) with 1GB RAM.

### Quick Fix Steps

1. **Delete current instance:**
```powershell
aws lightsail delete-instance --instance-name whovoted-app --region us-east-1
```

2. **Edit the deployment script:**
Open `WhoVoted/deploy/deploy-to-lightsail.ps1` and change line 13:
```powershell
# FROM:
$BUNDLE_ID = "nano_3_0"  # $5/month - 1 GB RAM, 1 vCPU, 40 GB SSD

# TO:
$BUNDLE_ID = "micro_3_0"  # $10/month - 1 GB RAM, 2 vCPUs, 60 GB SSD
```

3. **Redeploy:**
```powershell
cd WhoVoted/deploy
.\deploy-to-lightsail.ps1
```

## Alternative: Optimize for Smaller Instance

If you want to stay at $5/month, you could:

1. Remove old dataset files from the repository
2. Only load data files on-demand instead of at startup
3. Use a database instead of JSON files
4. Compress the geocoding cache

But upgrading to $10/month is the fastest solution.

## Even Better Alternative: Use Render

Render.com offers 512MB RAM on their free tier, but with better memory management:

1. Go to render.com
2. Connect GitHub repo
3. Create Web Service
4. Build command: `pip install -r backend/requirements.txt && pip install gunicorn`
5. Start command: `cd backend && gunicorn -w 1 --timeout 300 app:app`
6. Add environment variables
7. Deploy

The `-w 1` limits to 1 worker process to save memory.
