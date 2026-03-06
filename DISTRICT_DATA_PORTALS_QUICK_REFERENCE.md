# Texas Legislative Districts - Data Portals Quick Reference

**Last Updated:** March 6, 2026

## Data Portal URLs

### Congressional Districts (38 districts)
**Portal:** https://data.capitol.texas.gov/dataset/planc2333  
**Plan:** PLANC2333  
**Legislature:** 89th Legislature, 2nd C.S., 2025  
**Effective:** 2026 elections  
**Documentation:** `PLANC2333_ESSENTIAL_FILES.md`

### State Senate Districts (31 districts)
**Portal:** https://data.capitol.texas.gov/dataset/plans2168  
**Plan:** PLANS2168  
**Legislature:** 88th Legislature, Regular Session, 2023  
**Effective:** 2023-2026 elections  
**Documentation:** `PLANS2168_ESSENTIAL_FILES.md`

### State House Districts (150 districts)
**Portal:** https://data.capitol.texas.gov/dataset/planh2316  
**Plan:** PLANH2316  
**Legislature:** 88th Legislature, Regular Session, 2023  
**Effective:** 2023-2026 elections  
**Documentation:** `PLANH2316_ESSENTIAL_FILES.md`

## Quick Download Checklist

### Priority 1 Files (Download These First)

| File Type | Congressional | State Senate | State House |
|-----------|--------------|--------------|-------------|
| **Counties** | [PLANC2333_r150.xls](https://data.capitol.texas.gov/dataset/planc2333) | [PLANS2168_r150.xls](https://data.capitol.texas.gov/dataset/plans2168) | [PLANH2316_r150.xls](https://data.capitol.texas.gov/dataset/planh2316) |
| **Precincts** | [PLANC2333_r365_Prec24G.xls](https://data.capitol.texas.gov/dataset/planc2333) | [PLANS2168_r365_Prec2024 General.xls](https://data.capitol.texas.gov/dataset/plans2168) | [PLANH2316_r365_Prec2024 General.xls](https://data.capitol.texas.gov/dataset/planh2316) |
| **Voter Data** | [PLANC2333_r202_22G-24G.xls](https://data.capitol.texas.gov/dataset/planc2333) | [PLANS2168_r202_22G-24G.xls](https://data.capitol.texas.gov/dataset/plans2168) | [PLANH2316_r202_22G-24G.xls](https://data.capitol.texas.gov/dataset/planh2316) |
| **ZIP Codes** | [PLANC2333_r385.xls](https://data.capitol.texas.gov/dataset/planc2333) | [PLANS2168_r385_2024.xls](https://data.capitol.texas.gov/dataset/plans2168) | [PLANH2316_r385_2024.xls](https://data.capitol.texas.gov/dataset/planh2316) |

### Bulk Download Options

| District Type | Bulk ZIP File | Size | Link |
|--------------|---------------|------|------|
| Congressional | PLANC2333_All_Files_20251009.zip | ~500MB | [Download](https://data.capitol.texas.gov/dataset/planc2333) |
| State Senate | PLANS2168_All_Files_20250220.zip | ~400MB | [Download](https://data.capitol.texas.gov/dataset/plans2168) |
| State House | PLANH2316_All_Files_20250220.zip | ~600MB | [Download](https://data.capitol.texas.gov/dataset/planh2316) |

## File Naming Convention

All three district types use the same "r" number system:

| Code | Description | Example Files |
|------|-------------|---------------|
| r150 | Districts by County | Shows which counties are in each district |
| r155 | Split Counties | Counties divided between multiple districts |
| r365 | Precincts in District by County | All precincts per district |
| r370 | Split Precincts | Precincts divided between districts |
| r385 | ZIP Codes by District | ZIP codes per district |
| r100 | District Population Analysis | Demographics and population |
| r202 | District Population and Voter Data | Registration and turnout |
| r206 | District Election Analysis | Historical election results |
| r237 | Registration and Turnout with SSTO | Detailed turnout statistics |

## Download Instructions

### Step 1: Create Directory
```bash
mkdir -p WhoVoted/data/district_reference
cd WhoVoted/data/district_reference
```

### Step 2: Download Files
Visit each portal and download the Priority 1 files listed above.

### Step 3: Verify Downloads
```bash
ls -lh *.xls
```

You should see 12 XLS files (4 files × 3 district types).

### Step 4: Run Parser
```bash
cd ../..
python deploy/parse_district_files.py
```

## Expected Output

After running the parser, you'll have:

```
data/district_reference/
├── congressional_counties.json      (38 districts with counties)
├── congressional_precincts.json     (38 districts with precincts)
├── state_senate_counties.json       (31 districts with counties)
├── state_senate_precincts.json      (31 districts with precincts)
├── state_house_counties.json        (150 districts with counties)
└── state_house_precincts.json       (150 districts with precincts)
```

## Verification

### Check Congressional Districts
```bash
python -c "import json; f=open('data/district_reference/congressional_counties.json'); d=json.load(f); print(f'Parsed {len(d)} congressional districts')"
```

### Check State Senate Districts
```bash
python -c "import json; f=open('data/district_reference/state_senate_counties.json'); d=json.load(f); print(f'Parsed {len(d)} state senate districts')"
```

### Check State House Districts
```bash
python -c "import json; f=open('data/district_reference/state_house_counties.json'); d=json.load(f); print(f'Parsed {len(d)} state house districts')"
```

## Quick Reference Summary

| Metric | Congressional | State Senate | State House | Total |
|--------|--------------|--------------|-------------|-------|
| Districts | 38 | 31 | 150 | **219** |
| Portal Code | PLANC2333 | PLANS2168 | PLANH2316 | - |
| Term Length | 2 years | 4 years | 2 years | - |
| Avg Population | ~800K | ~900K | ~190K | - |
| Geographic Size | Large | Larger | Small | - |

## Support Documentation

- **Master Guide:** `ALL_DISTRICTS_REFERENCE_SYSTEM.md`
- **Integration Guide:** `DISTRICT_REFERENCE_COMPLETE_GUIDE.md`
- **Congressional:** `PLANC2333_ESSENTIAL_FILES.md`
- **State Senate:** `PLANS2168_ESSENTIAL_FILES.md`
- **State House:** `PLANH2316_ESSENTIAL_FILES.md`
- **Summary:** `COMPLETE_DISTRICT_SYSTEM_SUMMARY.md`

## Troubleshooting

### Parser fails to read Excel file
```bash
pip install xlrd openpyxl
```

### File not found errors
Verify files are in `WhoVoted/data/district_reference/` directory.

### Column detection issues
Check that you downloaded the correct "r" numbered files (r150, r365, etc.).

## Contact & Support

For issues with:
- **Data portals:** Texas Legislature Redistricting Office
- **Parser script:** Check `deploy/parse_district_files.py`
- **Documentation:** See files listed in Support Documentation section

---

**Quick Start:** Download 12 XLS files → Run parser → Get 6 JSON files with all 219 districts!
