# D15 Dashboard Deployment Guide

## Files to Deploy

Copy these files to the production server:

### 1. Dashboard Files
```bash
# From: WhoVoted/public/d15/
# To: /opt/whovoted/public/d15/

- index.html
- dashboard.js
- upload.html
```

### 2. Logo
```bash
# From: WhoVoted/public/assets/
# To: /opt/whovoted/public/assets/

- bobby-pulido-logo.png
```

### 3. District Boundaries
```bash
# From: WhoVoted/public/data/
# To: /opt/whovoted/public/data/

- districts.json (2.6 MB)
```

### 4. Backend API
```bash
# From: WhoVoted/backend/
# To: /opt/whovoted/backend/

- app.py (updated with D15 endpoints)
```

## Deployment Commands

### Option 1: Using SCP (if you have SSH key set up)

```bash
cd WhoVoted

# Dashboard files
scp public/d15/index.html root@politiquera.com:/opt/whovoted/public/d15/
scp public/d15/dashboard.js root@politiquera.com:/opt/whovoted/public/d15/
scp public/d15/upload.html root@politiquera.com:/opt/whovoted/public/d15/

# Logo
scp public/assets/bobby-pulido-logo.png root@politiquera.com:/opt/whovoted/public/assets/

# Districts data
scp public/data/districts.json root@politiquera.com:/opt/whovoted/public/data/

# Backend
scp backend/app.py root@politiquera.com:/opt/whovoted/backend/

# Restart backend
ssh root@politiquera.com "systemctl restart whovoted"
```

### Option 2: Using SFTP Client (FileZilla, WinSCP, etc.)

1. Connect to politiquera.com via SFTP
2. Navigate to `/opt/whovoted/`
3. Upload files to their respective directories
4. SSH into server and run: `systemctl restart whovoted`

### Option 3: Manual Copy via SSH

```bash
# SSH into server
ssh root@politiquera.com

# Create directories if needed
mkdir -p /opt/whovoted/public/d15
mkdir -p /opt/whovoted/public/data

# Then use your preferred method to upload files
# (FileZilla, WinSCP, rsync, etc.)

# After uploading, restart the backend
systemctl restart whovoted
```

## Verification

After deployment, verify:

1. **Dashboard loads**: https://politiquera.com/d15
2. **Logo displays**: Check the header shows Bobby Pulido logo
3. **No console errors**: Open browser DevTools (F12) and check Console
4. **API responds**: Should see empty data (0 votes) not 500 errors
5. **Upload works**: https://politiquera.com/d15/upload.html

## Troubleshooting

### Still seeing old version?
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check file timestamps on server
- Verify files were actually uploaded

### 404 for districts.json?
- Ensure `/opt/whovoted/public/data/districts.json` exists
- Check file permissions: `chmod 644 /opt/whovoted/public/data/districts.json`

### 500 error from API?
- Check backend logs: `journalctl -u whovoted -n 50`
- Verify app.py was updated
- Ensure backend restarted: `systemctl status whovoted`

### Logo not showing?
- Check `/opt/whovoted/public/assets/bobby-pulido-logo.png` exists
- Verify file permissions: `chmod 644 /opt/whovoted/public/assets/bobby-pulido-logo.png`

## Cache Busting

If users see old version, you can add a version parameter to the script tag in index.html:

```html
<script src="dashboard.js?v=20260303"></script>
```

Change the version number each time you deploy.
