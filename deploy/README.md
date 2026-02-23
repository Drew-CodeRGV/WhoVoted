# WhoVoted AWS Lightsail Deployment Guide

This directory contains scripts to deploy the WhoVoted application to AWS Lightsail.

## Cost

- **$5/month** for 1 GB RAM, 1 vCPU, 40 GB SSD, 2 TB transfer
- Plus AWS Location Service usage (geocoding costs)

## Prerequisites

1. AWS CLI installed and configured
2. AWS account with Lightsail permissions
3. Your AWS credentials (Access Key ID and Secret Access Key)

## Deployment Steps

### 1. Deploy the Instance

From your local machine (Windows PowerShell):

```powershell
cd WhoVoted/deploy
.\deploy-to-lightsail.ps1
```

This script will:
- Create a Lightsail instance named `whovoted-app`
- Set up Ubuntu 22.04
- Install Python, Nginx, and all dependencies
- Clone your GitHub repository
- Configure the application to run automatically

The script takes about 5-10 minutes to complete.

### 2. Open Firewall Port

After the instance is created, open port 80 for HTTP traffic:

```powershell
aws lightsail open-instance-public-ports --instance-name whovoted-app --port-info fromPort=80,toPort=80,protocol=tcp --region us-east-1
```

### 3. Configure AWS Credentials

SSH into your instance:

```bash
ssh -i whovoted-key.pem ubuntu@YOUR_INSTANCE_IP
```

Run the configuration script:

```bash
cd /opt/whovoted/deploy
chmod +x configure-env.sh
./configure-env.sh
```

Enter your AWS credentials when prompted.

### 4. Verify Deployment

Check that the application is running:

```bash
sudo supervisorctl status whovoted
```

View logs:

```bash
tail -f /opt/whovoted/logs/gunicorn-error.log
```

Access your application:

```
http://YOUR_INSTANCE_IP
```

Admin dashboard:

```
http://YOUR_INSTANCE_IP/admin
```

## Management Commands

### Restart Application

```bash
sudo supervisorctl restart whovoted
```

### View Logs

```bash
# Application logs
tail -f /opt/whovoted/logs/gunicorn-error.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# Supervisor logs
tail -f /opt/whovoted/logs/supervisor-error.log
```

### Update Application

```bash
cd /opt/whovoted
git pull origin main
source venv/bin/activate
pip install -r backend/requirements.txt
sudo supervisorctl restart whovoted
```

### Stop Application

```bash
sudo supervisorctl stop whovoted
```

### Start Application

```bash
sudo supervisorctl start whovoted
```

## File Locations

- Application: `/opt/whovoted/`
- Data files: `/opt/whovoted/data/`
- Logs: `/opt/whovoted/logs/`
- Uploads: `/opt/whovoted/uploads/`
- Environment: `/opt/whovoted/.env`
- Nginx config: `/etc/nginx/sites-available/whovoted`
- Supervisor config: `/etc/supervisor/conf.d/whovoted.conf`

## Troubleshooting

### Application won't start

Check logs:
```bash
tail -f /opt/whovoted/logs/supervisor-error.log
```

### Can't access the website

1. Check if Nginx is running:
```bash
sudo systemctl status nginx
```

2. Check if port 80 is open:
```bash
aws lightsail get-instance-port-states --instance-name whovoted-app --region us-east-1
```

### Geocoding not working

1. Verify AWS credentials in `/opt/whovoted/.env`
2. Check that AWS Location Service is set up in your AWS account
3. View application logs for errors

### Out of disk space

Check disk usage:
```bash
df -h
```

Clean up old uploads:
```bash
rm -rf /opt/whovoted/uploads/*
```

## Deleting the Instance

To delete the instance and stop charges:

```powershell
aws lightsail delete-instance --instance-name whovoted-app --region us-east-1
```

## Security Notes

1. The default admin password is `admin2026!` - change this in production
2. Consider setting up HTTPS with Let's Encrypt
3. The `.env` file contains sensitive credentials - keep it secure
4. Consider using AWS Secrets Manager for production credentials

## Adding a Custom Domain

1. Register a domain or use an existing one
2. Create a static IP in Lightsail:
```bash
aws lightsail allocate-static-ip --static-ip-name whovoted-ip --region us-east-1
aws lightsail attach-static-ip --static-ip-name whovoted-ip --instance-name whovoted-app --region us-east-1
```

3. Point your domain's A record to the static IP
4. Update Nginx configuration with your domain name
5. Set up SSL with Let's Encrypt (optional but recommended)

## Support

For issues, check:
- Application logs: `/opt/whovoted/logs/`
- GitHub repository: https://github.com/Drew-CodeRGV/WhoVoted
- AWS Lightsail documentation: https://docs.aws.amazon.com/lightsail/
