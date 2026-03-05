# Fix D15 Dashboard - Quick Instructions

## The Problem
The D15 dashboard frontend can't reach the backend API because nginx routing is misconfigured.

## The Solution
Run this ONE command on the server:

```bash
bash /opt/whovoted/deploy/fix_d15_nginx.sh
```

This script will:
1. Check if d15-backend service is running
2. Test the backend directly (should work)
3. Show current nginx config
4. Fix the nginx routing configuration
5. Test nginx config syntax
6. Reload nginx
7. Test the API through nginx (should now work)

## What It Does
- Removes any broken `/d15api/` location blocks
- Adds a clean proxy configuration that routes `https://politiquera.com/d15api/*` to `http://127.0.0.1:5001/d15api/*`
- Backs up your config before making changes

## After Running
1. Go to https://politiquera.com/d15/
2. Click the purple upload button
3. Upload your Excel file
4. It should work!

## If It Still Doesn't Work
The script will show you exactly what's failing. Look for:
- "d15-backend" service not running → `systemctl start d15-backend`
- Backend not responding on port 5001 → Check `/opt/whovoted/data/d15_elections.db` exists
- nginx test failed → Check the error message in the script output
