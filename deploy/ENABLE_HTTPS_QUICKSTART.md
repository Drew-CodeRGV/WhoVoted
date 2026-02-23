# Enable HTTPS - Quick Start

## 3-Step Setup for politiquera.com

### Step 1: Open Port 443 (from your local machine)

```powershell
aws lightsail open-instance-public-ports --instance-name whovoted-app --port-info fromPort=443,toPort=443,protocol=tcp --region us-east-1
```

### Step 2: Run Setup Script (SSH into server)

```bash
# Upload script
scp -i deploy/whovoted-key.pem deploy/enable-https.sh ubuntu@54.164.71.129:/tmp/

# SSH into server
ssh -i deploy/whovoted-key.pem ubuntu@54.164.71.129

# Run script
sudo bash /tmp/enable-https.sh
```

### Step 3: Test

Visit https://politiquera.com 🔒

---

## Manual Setup (Alternative)

If the script doesn't work, run these commands on your server:

```bash
# 1. Install Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# 2. Update Nginx config
sudo nano /etc/nginx/sites-available/whovoted
# Change: server_name politiquera.com www.politiquera.com;

# 3. Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx

# 4. Get SSL certificate
sudo certbot --nginx -d politiquera.com -d www.politiquera.com

# 5. Follow prompts and choose option 2 (redirect HTTP to HTTPS)
```

---

## Verify Setup

✅ Visit https://politiquera.com  
✅ See padlock icon in browser  
✅ HTTP redirects to HTTPS  
✅ Certificate is valid  

---

## Certificate Auto-Renewal

Certificates automatically renew every 90 days. No action needed!

Test renewal:
```bash
sudo certbot renew --dry-run
```

---

## Troubleshooting

**Port 443 not accessible?**
```powershell
aws lightsail get-instance --instance-name whovoted-app --region us-east-1 --query "instance.networking.ports"
```

**DNS not resolving?**
```bash
nslookup politiquera.com
# Should return: 54.164.71.129
```

**Certificate failed?**
```bash
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

---

See `HTTPS_SETUP_GUIDE.md` for detailed instructions.
