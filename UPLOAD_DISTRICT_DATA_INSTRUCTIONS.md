# Upload District Data to Server - Instructions

## Quick Method (Recommended)

### Step 1: Update Configuration

Edit the upload script with your server details:

**For Linux/Mac:** `deploy/upload_district_data_to_server.sh`  
**For Windows:** `deploy/upload_district_data_to_server.ps1`

Update these lines:
```bash
SERVER_USER="your_username"      # e.g., "ubuntu"
SERVER_HOST="your_server_ip"     # e.g., "123.45.67.89"
SERVER_PATH="/home/ubuntu/WhoVoted/data/district_reference"
```

### Step 2: Run Upload Script

**Linux/Mac:**
```bash
cd WhoVoted
chmod +x deploy/upload_district_data_to_server.sh
./deploy/upload_district_data_to_server.sh
```

**Windows PowerShell:**
```powershell
cd WhoVoted
.\deploy\upload_district_data_to_server.ps1
```

### Step 3: Run Parser on Server

SSH to your server and run:
```bash
ssh your_username@your_server_ip
cd /home/ubuntu/WhoVoted
python deploy/parse_district_files.py
```

---

## Manual Method

If you prefer to do it manually:

### Step 1: Upload ZIP Files

From your local machine:

```bash
# Upload Congressional districts
scp data/district_reference/PLANC2333_All_Files_*.zip \
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/

# Upload State Senate districts
scp data/district_reference/PLANS2168_All_Files_*.zip \
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/

# Upload State House districts
scp data/district_reference/PLANH2316_All_Files_*.zip \
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/
```

**Windows (PowerShell):**
```powershell
scp data\district_reference\PLANC2333_All_Files_*.zip `
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/

scp data\district_reference\PLANS2168_All_Files_*.zip `
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/

scp data\district_reference\PLANH2316_All_Files_*.zip `
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/
```

### Step 2: SSH to Server

```bash
ssh your_username@your_server_ip
```

### Step 3: Extract ZIP Files

```bash
cd /home/ubuntu/WhoVoted/data/district_reference

# Extract all ZIP files
unzip -o "PLANC2333_All_Files_*.zip"
unzip -o "PLANS2168_All_Files_*.zip"
unzip -o "PLANH2316_All_Files_*.zip"

# Verify extraction
ls -lh *.xls | head -20
echo "Total XLS files: $(ls -1 *.xls | wc -l)"
```

### Step 4: Run Parser

```bash
cd /home/ubuntu/WhoVoted
python deploy/parse_district_files.py
```

---

## Expected Results

After running the parser, you should see:

```
================================================================================
PARSING TEXAS DISTRICT REFERENCE FILES
================================================================================

================================================================================
CONGRESSIONAL DISTRICTS (PLANC2333)
================================================================================

Parsing PLANC2333_r150.xls...
  Loaded XXX rows
  ✓ Parsed 38 districts

Parsing PLANC2333_r365_Prec24G.xls...
  Loaded XXX rows
  ✓ Parsed 38 districts

================================================================================
STATE SENATE DISTRICTS (PLANS2168)
================================================================================

Parsing PLANS2168_r150.xls...
  ✓ Parsed 31 districts

Parsing PLANS2168_r365_Prec2024 General.xls...
  ✓ Parsed 31 districts

================================================================================
STATE HOUSE DISTRICTS (PLANH2316)
================================================================================

Parsing PLANH2316_r150.xls...
  ✓ Parsed 150 districts

Parsing PLANH2316_r365_Prec2024 General.xls...
  ✓ Parsed 150 districts

================================================================================
✓ PARSING COMPLETE
================================================================================
```

## Verify Output Files

Check that these files were created:

```bash
ls -lh data/district_reference/*.json
```

You should see:
- `congressional_counties.json` (38 districts)
- `congressional_precincts.json` (38 districts)
- `state_senate_counties.json` (31 districts)
- `state_senate_precincts.json` (31 districts)
- `state_house_counties.json` (150 districts)
- `state_house_precincts.json` (150 districts)

## Troubleshooting

### "unzip: command not found"

Install unzip:
```bash
sudo apt-get update
sudo apt-get install unzip
```

### "Permission denied"

Make sure the directory exists and you have write permissions:
```bash
mkdir -p /home/ubuntu/WhoVoted/data/district_reference
chmod 755 /home/ubuntu/WhoVoted/data/district_reference
```

### "No such file or directory"

Verify the ZIP files were uploaded:
```bash
ls -lh /home/ubuntu/WhoVoted/data/district_reference/*.zip
```

### Parser fails with "xlrd" or "openpyxl" error

Install required Python packages:
```bash
pip install xlrd openpyxl pandas
```

## Alternative: Upload Individual XLS Files

If the ZIP files are too large, you can upload just the essential XLS files:

```bash
# Upload only the critical files
scp data/district_reference/PLANC2333_r150.xls \
    data/district_reference/PLANC2333_r365_Prec24G.xls \
    data/district_reference/PLANS2168_r150.xls \
    data/district_reference/PLANS2168_r365_Prec2024\ General.xls \
    data/district_reference/PLANH2316_r150.xls \
    data/district_reference/PLANH2316_r365_Prec2024\ General.xls \
    your_username@your_server_ip:/home/ubuntu/WhoVoted/data/district_reference/
```

Then run the parser directly (no extraction needed).

## Summary

1. Upload ZIP files to server (or use script)
2. SSH to server
3. Extract ZIP files
4. Run parser
5. Verify 6 JSON files were created

Total time: ~5-10 minutes depending on file sizes and connection speed.
