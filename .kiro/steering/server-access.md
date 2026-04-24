---
inclusion: auto
---

# Deployment Workflow

## MANDATORY: Git-Based Deployment

### NEVER directly upload files to server
### ALWAYS use this workflow:

1. **Write code locally** in `WhoVoted/` directory
2. **Commit to Git** (user handles this)
3. **SSH to server and pull**:
   ```bash
   ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
   cd /opt/whovoted
   git pull origin main
   ```

### For immediate testing only:
```bash
# Upload single file for testing
scp -i WhoVoted/deploy/whovoted-key.pem <file> ubuntu@politiquera.com:/opt/whovoted/deploy/

# Then still do git pull to sync
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && git pull"
```

## SSH Connection
- **Username**: `ubuntu@` (NEVER `root@`)
- **Hostname**: `politiquera.com`
- **Key**: `WhoVoted/deploy/whovoted-key.pem`

## Server Paths
- Project: `/opt/whovoted`
- Scripts: `/opt/whovoted/deploy/`
- Database: `/opt/whovoted/data/whovoted.db`
- Public: `/opt/whovoted/public/`
- Districts: `/opt/whovoted/public/data/districts.json`
