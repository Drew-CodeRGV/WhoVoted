---
inclusion: manual
---

# Secrets Management

## Environment File

**Location**: `/opt/whovoted/.env` (on server) / `WhoVoted/backend/.env` (local dev)
**NOT in git**: `.env` is in `.gitignore`. Only `.env.example` is committed.

## Environment Variables

| Variable | Purpose | Origin | Rotation |
|----------|---------|--------|----------|
| `ADMIN_USERNAME` | Admin dashboard login | Hand-set | Change if compromised |
| `ADMIN_PASSWORD` | Admin dashboard login | Hand-set | Change if compromised |
| `SECRET_KEY` | Flask session signing | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Rotate quarterly |
| `GOOGLE_CLIENT_ID` | Google SSO | Google Cloud Console → OAuth 2.0 | Rarely changes |
| `GOOGLE_CLIENT_SECRET` | Google SSO | Google Cloud Console → OAuth 2.0 | Rarely changes |
| `AWS_ACCESS_KEY_ID` | AWS services (SES, SNS, Location) | AWS IAM Console | Rotate quarterly |
| `AWS_SECRET_ACCESS_KEY` | AWS services | AWS IAM Console | Rotate quarterly |
| `AWS_DEFAULT_REGION` | AWS region | Hand-set (`us-east-1`) | Never |
| `AWS_LOCATION_PLACE_INDEX` | AWS Location geocoding | AWS Console → Location Service | Never |
| `STRIPE_PAYMENT_LINK_URL` | Stripe Payment Link for credits | Stripe Dashboard → Payment Links | If link is compromised |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature verification | Stripe Dashboard → Webhooks → Signing secret | If endpoint is recreated |
| `NOMINATIM_USER_AGENT` | Nominatim API identification | Hand-set | Never |
| `CORS_ORIGINS` | Allowed CORS origins | Hand-set | When domains change |

## What's in .gitignore

```
backend/.env
deploy/whovoted-key.pem
*.pem
data/whovoted.db
data/*.json
logs/
```

## SSH Key

- **File**: `deploy/whovoted-key.pem`
- **Purpose**: SSH access to production server
- **User**: `ubuntu@politiquera.com`
- **Rotation**: If compromised, generate new key pair in AWS Lightsail console, update `~/.ssh/authorized_keys` on server.

## Rotation Procedure

1. Generate new value (see Origin column above)
2. SSH to server: `ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com`
3. Edit: `nano /opt/whovoted/.env`
4. Restart: `sudo supervisorctl restart whovoted`
5. Verify: `curl -s https://politiquera.com/api/config | jq .`

## Rules

- Never commit `.env` or `*.pem` files.
- Never echo secret values in logs or API responses.
- Never hardcode secrets in Python source files.
- Access secrets via `os.getenv()` or `Config` class in `backend/config.py`.
- If a secret appears in a git commit, rotate it immediately — git history is permanent.
