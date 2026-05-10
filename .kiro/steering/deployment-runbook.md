---
inclusion: manual
---

# Deployment Runbook

## Standard Deploy (Code Change)

```bash
# 1. Local: commit and push
git add -A && git commit -m "description" && git push origin main

# 2. SSH to server
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com

# 3. Pull changes
cd /opt/whovoted && git pull origin main

# 4. Restart gunicorn (if backend code changed)
sudo supervisorctl restart whovoted

# 5. If d15_app.py changed:
sudo supervisorctl restart d15

# 6. If nginx config changed:
sudo nginx -t && sudo systemctl reload nginx
```

## When to Restart What

| Changed | Restart |
|---------|---------|
| `backend/*.py` | `sudo supervisorctl restart whovoted` |
| `backend/d15_app.py` | `sudo supervisorctl restart d15` |
| `public/*` (HTML/JS/CSS) | Nothing — nginx serves static files directly |
| `gunicorn_config.py` | `sudo supervisorctl restart whovoted` |
| nginx config | `sudo nginx -t && sudo systemctl reload nginx` |
| `.env` | `sudo supervisorctl restart whovoted` |
| `deploy/*.py` (cron scripts) | Nothing — next cron run picks up changes |

## Rollback

```bash
# On server:
cd /opt/whovoted
git log --oneline -5          # find the commit to revert to
git revert HEAD               # revert last commit (safe)
# OR
git reset --hard <commit>     # nuclear option — loses uncommitted changes
sudo supervisorctl restart whovoted
```

## Certbot / TLS

- Certificate: Let's Encrypt, auto-renewed by certbot
- Renewal check: `sudo certbot renew --dry-run`
- Renewal cron: managed by certbot's systemd timer (`systemctl list-timers | grep certbot`)
- Certificate path: `/etc/letsencrypt/live/politiquera.com/`
- Renewal cadence: every 60 days (certificates valid for 90 days)

## Supervisor Commands

```bash
sudo supervisorctl status              # check all processes
sudo supervisorctl restart whovoted    # restart main app
sudo supervisorctl restart d15         # restart d15 app
sudo supervisorctl stop whovoted       # stop (for maintenance)
sudo supervisorctl start whovoted      # start after stop
sudo supervisorctl tail whovoted       # last 1600 bytes of stdout
sudo supervisorctl tail -f whovoted    # follow stdout
```

## Gotchas

- **Never run as root**: SSH as `ubuntu`, use `sudo` for supervisor/nginx.
- **Git conflicts**: If server has uncommitted changes, `git stash` before `git pull`.
- **Disk full**: Check `/opt/whovoted/logs/` and `/opt/whovoted/data/` — logs can grow unbounded.
- **Ollama after restart**: If the Lightsail instance reboots, Ollama may not auto-start. Check: `curl http://127.0.0.1:11434/api/tags`. Fix: `ollama serve &`.
- **WAL checkpoint**: If DB grows large, run `sqlite3 /opt/whovoted/data/whovoted.db "PRAGMA wal_checkpoint(TRUNCATE);"`.
