# HTTPS Setup Guide for politiquera.com

This guide will help you enable HTTPS (SSL/TLS) for your politiquera.com domain using Let's Encrypt free SSL certificates.

## Prerequisites

✅ Domain name (politiquera.com) is mapped to your Lightsail IP (54.164.71.129)  
✅ DNS records are propagated (A record pointing to 54.164.71.129)  
✅ Application is running on Lightsail  
✅ Port 80 is open (already done)

## Quick Setup (Automated)

### Step 1: Open Port 443 (HTTPS) in Lightsail

From your local machine, run:

```powershell
aws lightsail open-instance-public-ports --instance-name whovoted-app --port-info fromPort=443,toPort=443,protocol=tcp --region us-east-1
```

### Step 2: Upload and Run the Setup Script

```powershell
# From WhoVoted/deploy directory
scp -i whovoted-key.pem enable-https.sh ubuntu@54.164.71.129:/tmp/
ssh -i whovoted-key.pem ubuntu@54.164.71.129
```

Then on the server:

```bash
sudo bash /tmp/enable-https.sh
```

The script will:
1. Install Certbot (Let's Encrypt client)
2. Update Nginx configuration for your domain
3. Obtain SSL certificate
4. Configure automatic HTTPS redirect
5. Set up automatic certificate renewal

### Step 3: Test Your Site

Visit https://politiquera.com - you should see the secure padlock icon! 🔒

---

## Manual Setup (Step-by-Step)

If you prefer to do it manually or the script fails, follow these steps:

### 1. Open Port 443 in Lightsail

```powershell
aws lightsail open-instance-public-ports --instance-name whovoted-app --port-info fromPort=443,toPort=443,protocol=tcp --region us-east-1
```

### 2. SSH into Your Instance

```bash
ssh -i whovoted-key.pem ubuntu@54.164.71.129
```

### 3. Install Certbot

```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

### 4. Update Nginx Configuration

Edit the Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/whovoted
```

Update the `server_name` line to include your domain:

```nginx
server {
    listen 80;
    server_name politiquera.com www.politiquera.com;
    
    # ... rest of configuration stays the same
}
```

Save and exit (Ctrl+X, Y, Enter).

### 5. Test Nginx Configuration

```bash
sudo nginx -t
```

Should output: "syntax is ok" and "test is successful"

### 6. Reload Nginx

```bash
sudo systemctl reload nginx
```

### 7. Obtain SSL Certificate

```bash
sudo certbot --nginx -d politiquera.com -d www.politiquera.com
```

Follow the prompts:
- Enter your email address
- Agree to Terms of Service (Y)
- Choose whether to share email with EFF (optional)
- Choose option 2 to redirect HTTP to HTTPS

### 8. Verify HTTPS is Working

Visit https://politiquera.com in your browser. You should see:
- 🔒 Padlock icon in address bar
- "Connection is secure" message
- HTTP automatically redirects to HTTPS

---

## What Certbot Does

Certbot automatically:

1. **Obtains SSL certificate** from Let's Encrypt
2. **Configures Nginx** to use the certificate
3. **Sets up HTTP to HTTPS redirect**
4. **Creates renewal cron job** (certificates auto-renew every 90 days)

### Certificate Files Location

- Certificate: `/etc/letsencrypt/live/politiquera.com/fullchain.pem`
- Private Key: `/etc/letsencrypt/live/politiquera.com/privkey.pem`

---

## Nginx Configuration After Certbot

After running Certbot, your Nginx config will look like this:

```nginx
server {
    listen 80;
    server_name politiquera.com www.politiquera.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name politiquera.com www.politiquera.com;

    # SSL certificate files (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/politiquera.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/politiquera.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Root directory for static files
    root /opt/whovoted/public;
    index index.html;

    # ... rest of your configuration
}
```

---

## Certificate Management

### Check Certificate Status

```bash
sudo certbot certificates
```

### Manual Certificate Renewal

```bash
sudo certbot renew
```

### Test Renewal Process

```bash
sudo certbot renew --dry-run
```

### Automatic Renewal

Certbot automatically creates a systemd timer that runs twice daily to check for expiring certificates. No action needed!

Check the timer status:

```bash
sudo systemctl status certbot.timer
```

---

## Troubleshooting

### Issue: Port 443 Connection Refused

**Solution:** Make sure port 443 is open in Lightsail firewall:

```powershell
aws lightsail open-instance-public-ports --instance-name whovoted-app --port-info fromPort=443,toPort=443,protocol=tcp --region us-east-1
```

### Issue: DNS Not Resolving

**Solution:** Verify DNS records are correct:

```bash
nslookup politiquera.com
```

Should return: 54.164.71.129

If not, update your DNS A record to point to the correct IP.

### Issue: Certificate Validation Failed

**Solution:** Make sure:
1. Domain DNS is pointing to your server IP
2. Port 80 is accessible (Let's Encrypt uses HTTP challenge)
3. Nginx is running and serving the domain

### Issue: Mixed Content Warnings

**Solution:** Update any hardcoded HTTP URLs in your HTML/JS to use HTTPS or relative URLs.

Check `public/index.html` for any `http://` URLs and change them to `https://` or remove the protocol entirely (`//example.com`).

---

## Security Best Practices

### 1. Enable HSTS (HTTP Strict Transport Security)

Add to your Nginx HTTPS server block:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 2. Enable Security Headers

Add these headers to your Nginx HTTPS server block:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

### 3. Test SSL Configuration

Use SSL Labs to test your SSL configuration:
https://www.ssllabs.com/ssltest/analyze.html?d=politiquera.com

Aim for an A or A+ rating.

---

## Updating Application URLs

After enabling HTTPS, update these references in your code:

### 1. Update Meta Tags in index.html

```html
<meta property="og:url" content="https://politiquera.com">
```

### 2. Update Any Hardcoded URLs

Search for `http://` in your codebase and update to `https://` where appropriate.

---

## Cost

✅ **FREE** - Let's Encrypt certificates are completely free!

The only cost is your existing Lightsail instance ($10/month).

---

## Certificate Expiration

- **Validity:** 90 days
- **Auto-renewal:** Happens automatically 30 days before expiration
- **Monitoring:** Let's Encrypt will email you if renewal fails

---

## Quick Reference Commands

### Check Certificate Status
```bash
sudo certbot certificates
```

### Renew Certificate Manually
```bash
sudo certbot renew
```

### Test Renewal
```bash
sudo certbot renew --dry-run
```

### View Nginx Configuration
```bash
sudo cat /etc/nginx/sites-available/whovoted
```

### Reload Nginx After Changes
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Check Nginx Error Logs
```bash
sudo tail -f /var/log/nginx/error.log
```

---

## Summary

After completing this setup:

✅ Your site will be accessible via HTTPS  
✅ HTTP traffic will automatically redirect to HTTPS  
✅ SSL certificate will auto-renew every 90 days  
✅ Your site will show the secure padlock icon 🔒  
✅ User data will be encrypted in transit  

**Your site will be available at:**
- https://politiquera.com ✅
- https://www.politiquera.com ✅
- http://politiquera.com → redirects to HTTPS
- http://www.politiquera.com → redirects to HTTPS

---

**Need Help?**

If you encounter any issues, check:
1. Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
2. Certbot logs: `sudo tail -f /var/log/letsencrypt/letsencrypt.log`
3. DNS resolution: `nslookup politiquera.com`
4. Port 443 is open in Lightsail firewall

---

**Last Updated:** February 22, 2026
