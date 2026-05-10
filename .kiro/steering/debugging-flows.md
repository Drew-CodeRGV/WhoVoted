---
inclusion: manual
---

# Debugging Flows

## Gunicorn Won't Start

```bash
sudo supervisorctl status whovoted          # check status
sudo supervisorctl tail whovoted stderr     # last error output
tail -20 /opt/whovoted/logs/gunicorn-error.log
```

Common causes:
- Syntax error in Python: check the traceback in stderr
- Port 5000 already in use: `sudo lsof -i :5000`
- Missing dependency: `source /opt/whovoted/venv/bin/activate && pip install -r backend/requirements.txt`
- Bad .env: `python -c "from backend.config import Config; Config.validate()"`

## EVR Scraper Failing

```bash
tail -50 /opt/whovoted/data/evr_scraper.log
cat /opt/whovoted/data/evr_scraper_state.json
curl -s "https://goelect.txelections.civixapps.com/api-ivis-system/api/v1/getFile?type=EVR_ELECTION" | head -100
```

Common causes:
- Civix API endpoint changed or is down
- ELECTION_FILTERS doesn't match current election names
- Network timeout (Lightsail → Civix)
- Python import error (check venv activation in cron)

## Geocoding Slow or Failing

```bash
# Check Nominatim rate
curl -s "https://nominatim.openstreetmap.org/search?q=McAllen+TX&format=json" | jq '.[0]'
# Check AWS Location fallback
python3 -c "import boto3; c=boto3.client('location'); print(c.search_place_index_for_text(IndexName='WhoVotedPlaceIndex', Text='McAllen TX'))"
# Check geocoding cache size
wc -l /opt/whovoted/data/geocoded_addresses.json
```

Common causes:
- Nominatim rate-limited (1 req/s enforced)
- AWS credentials expired: `aws sts get-caller-identity`
- Cache file corrupted: delete and let it rebuild

## District Counts Look Wrong

```bash
sqlite3 /opt/whovoted/data/whovoted.db "SELECT congressional_district, COUNT(*) FROM voters WHERE county='Hidalgo' GROUP BY congressional_district;"
sqlite3 /opt/whovoted/data/whovoted.db "SELECT district_type, district_number, total_voters FROM district_counts_cache WHERE county='Hidalgo';"
# Check if districts.json is valid
python3 -c "import json; d=json.load(open('/opt/whovoted/public/data/districts.json')); print(len(d['features']), 'districts')"
```

Common causes:
- districts.json is stale or corrupted
- Precinct centroids shifted after new voter data import
- VTD vintage issue (precinct was split)
- Cache not rebuilt after data change: run `deploy/regenerate_all_district_caches_fast.py`

## Ollama Unresponsive

```bash
curl http://127.0.0.1:11434/api/tags
systemctl status ollama
ollama list
```

Common causes:
- Ollama not running after server reboot: `ollama serve &`
- Out of memory (4GB box, model needs ~4GB): check `free -h`
- Model not pulled: `ollama pull llama3.2:latest`

## Nginx 502 Bad Gateway

```bash
sudo tail -20 /var/log/nginx/error.log
sudo supervisorctl status
curl -s http://127.0.0.1:5000/api/config
```

Common causes:
- Gunicorn not running: `sudo supervisorctl restart whovoted`
- Wrong upstream port in nginx config
- Gunicorn socket timeout: check `gunicorn_config.py` timeout setting

## Disk Full

```bash
df -h /opt/whovoted
du -sh /opt/whovoted/logs/
du -sh /opt/whovoted/data/
du -sh /opt/whovoted/public/cache/
ls -lhS /opt/whovoted/logs/ | head -5
```

Fix:
- Truncate logs: `> /opt/whovoted/logs/gunicorn-error.log`
- WAL checkpoint: `sqlite3 /opt/whovoted/data/whovoted.db "PRAGMA wal_checkpoint(TRUNCATE);"`
- Remove old cache files: `find /opt/whovoted/public/cache -mtime +30 -delete`
- Remove old uploads: `find /opt/whovoted/uploads -mtime +7 -delete`
