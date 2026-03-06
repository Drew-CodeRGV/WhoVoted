# Quick Upload Commands - Copy & Paste

## Option 1: Use Upload Script (Easiest)

### Edit Configuration First
Open `deploy/upload_district_data_to_server.ps1` and update:
- `$SERVER_USER = "ubuntu"` (or your username)
- `$SERVER_HOST = "your.server.ip"`

### Run Script
```powershell
cd WhoVoted
.\deploy\upload_district_data_to_server.ps1
```

---

## Option 2: Manual SCP Commands

Replace `ubuntu@your.server.ip` with your actual server details.

### Upload ZIP Files

```powershell
# From WhoVoted directory
cd data\district_reference

# Upload Congressional (if you have it)
scp PLANC2333_All_Files_*.zip ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/

# Upload State Senate (if you have it)
scp PLANS2168_All_Files_*.zip ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/

# Upload State House (if you have it)
scp PLANH2316_All_Files_*.zip ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
```

### Or Upload Individual XLS Files (if you already extracted them)

```powershell
# Upload Congressional files
scp planc2333_r150.xls ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
scp planc2333_r365_prec24g.xls ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/

# Upload State Senate files (if you have them)
scp plans2168_r150.xls ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
scp plans2168_r365_prec2024_general.xls ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/

# Upload State House files (if you have them)
scp planh2316_r150.xls ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
scp planh2316_r365_prec2024_general.xls ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
```

---

## On Server: Extract and Parse

### SSH to Server
```bash
ssh ubuntu@your.server.ip
```

### Extract ZIP Files (if you uploaded ZIPs)
```bash
cd /home/ubuntu/WhoVoted/data/district_reference

# Install unzip if needed
sudo apt-get install unzip -y

# Extract all ZIP files
unzip -o "*.zip"

# Verify
ls -lh *.xls | head -20
```

### Run Parser
```bash
cd /home/ubuntu/WhoVoted

# Install dependencies if needed
pip install pandas xlrd openpyxl

# Run parser
python deploy/parse_district_files.py
```

### Verify Output
```bash
ls -lh data/district_reference/*.json
```

You should see 6 JSON files created.

---

## Quick Status Check

### Check what you have locally
```powershell
cd WhoVoted\data\district_reference
Get-ChildItem *.zip, *.xls | Select-Object Name, @{Name="Size(MB)";Expression={[math]::Round($_.Length/1MB, 2)}}
```

### Check what's on server
```bash
ssh ubuntu@your.server.ip "ls -lh /home/ubuntu/WhoVoted/data/district_reference/*.{zip,xls,json} 2>/dev/null"
```

---

## Troubleshooting

### Can't connect to server
```powershell
# Test SSH connection
ssh ubuntu@your.server.ip "echo 'Connection successful'"
```

### Permission denied
```bash
# On server, fix permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/WhoVoted
chmod -R 755 /home/ubuntu/WhoVoted
```

### Parser fails
```bash
# On server, install dependencies
pip install --upgrade pandas xlrd openpyxl
```

---

## Summary

1. **Upload**: Use script or SCP commands above
2. **SSH**: `ssh ubuntu@your.server.ip`
3. **Extract**: `cd /home/ubuntu/WhoVoted/data/district_reference && unzip -o "*.zip"`
4. **Parse**: `cd /home/ubuntu/WhoVoted && python deploy/parse_district_files.py`
5. **Verify**: `ls -lh data/district_reference/*.json`

Done! You'll have all 219 districts parsed and ready to use.
