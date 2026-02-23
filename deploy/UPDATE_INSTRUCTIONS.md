# Update Instructions for Lightsail Instance

## Changes Pushed to GitHub

The loading indicator integration has been completed and pushed to GitHub.

**File updated:**
- `public/data.js` - Added loading indicator show/hide logic

## How to Update Your Lightsail Instance

### Option 1: Quick Update via SSH (Recommended)

Run this single command from your local machine (from the `WhoVoted/deploy` directory):

```powershell
ssh -i whovoted-key.pem ubuntu@54.164.71.129 "cd /opt/whovoted && git pull origin main && sudo supervisorctl restart whovoted"
```

This will:
1. Pull the latest changes from GitHub
2. Restart the application automatically

### Option 2: Manual Update via SSH

1. **SSH into your instance:**
   ```powershell
   ssh -i whovoted-key.pem ubuntu@54.164.71.129
   ```

2. **Navigate to the application directory:**
   ```bash
   cd /opt/whovoted
   ```

3. **Pull the latest changes:**
   ```bash
   git pull origin main
   ```

4. **Restart the application:**
   ```bash
   sudo supervisorctl restart whovoted
   ```

5. **Verify it's running:**
   ```bash
   sudo supervisorctl status whovoted
   ```

6. **Exit SSH:**
   ```bash
   exit
   ```

### Option 3: If SSH Connection Times Out

If you can't connect via SSH, the instance might be stopped or the IP might have changed.

**Check instance status:**
```powershell
aws lightsail get-instance --instance-name whovoted-app --region us-east-1
```

**Start the instance if it's stopped:**
```powershell
aws lightsail start-instance --instance-name whovoted-app --region us-east-1
```

**Get the current public IP:**
```powershell
aws lightsail get-instance --instance-name whovoted-app --region us-east-1 --query "instance.publicIpAddress"
```

## What Changed

The loading indicator now:
- ✅ Shows when the page first loads
- ✅ Shows when switching between datasets
- ✅ Hides automatically when data is ready
- ✅ Hides on errors to prevent getting stuck

## Testing the Update

After updating, visit your application at:
- http://54.164.71.129

You should now see a loading spinner with "Loading map data..." text when:
1. The page first loads
2. You switch datasets using the dropdown

## Troubleshooting

**If the update doesn't work:**

1. Check if the application is running:
   ```bash
   sudo supervisorctl status whovoted
   ```

2. View recent logs:
   ```bash
   tail -50 /opt/whovoted/logs/gunicorn-error.log
   ```

3. Force restart:
   ```bash
   sudo supervisorctl restart whovoted
   ```

4. Check for git conflicts:
   ```bash
   cd /opt/whovoted
   git status
   ```

   If there are conflicts, reset to the latest version:
   ```bash
   git fetch origin
   git reset --hard origin/main
   sudo supervisorctl restart whovoted
   ```

## Next Steps

After updating, you may want to:
1. Configure AWS credentials (if not done yet) - see DEPLOYMENT_INFO.txt
2. Test the loading indicator by switching between datasets
3. Upload new voter data via the admin dashboard

---

**Need help?** Check the logs or restart the application using the commands above.
