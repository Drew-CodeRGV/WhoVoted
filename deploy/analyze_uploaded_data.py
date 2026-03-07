#!/usr/bin/env python3
"""
Analyze all uploaded district reference data to verify completeness
"""
import os
from pathlib import Path
import zipfile

DATA_DIR = Path('/opt/whovoted/data/district_reference')

def check_file_exists(filename):
    """Check if a file exists and return its size"""
    path = DATA_DIR / filename
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        return True, f"{size_mb:.1f}MB"
    return False, "MISSING"

def analyze_zip_contents(zip_file):
    """Analyze contents of a zip file"""
    path = DATA_DIR / zip_file
    if not path.exists():
        return []
    
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            return [f for f in zf.namelist() if f.endswith(('.shp', '.dbf', '.shx', '.prj'))]
    except:
        return []

print("="*80)
print("DISTRICT REFERENCE DATA ANALYSIS")
print("="*80)

# Critical VTD (Precinct-Level) Files
print("\n[1] VTD (Precinct-Level) Files - CRITICAL FOR ACCURACY")
print("-" * 80)

vtd_files = {
    'Congressional (PLANC2333)': [
        'PLANC2333_r110_VTD24G.xls',  # Main VTD file
        'PLANC2333_r371_VTD24G.xls',  # VTD summary
        'PLANC2333_r381_VTD24G.xls',  # VTD detail
    ],
    'State Senate (PLANS2168)': [
        'PLANS2168_r110_VTD2024 General.xls',
        'PLANS2168_r110_VTD2024 Primary Election.xls',
        'PLANS2168_r371_VTD2024 General.xls',
        'PLANS2168_r381_VTD2024 General.xls',
    ],
    'State House (PLANH2316)': [
        'PLANH2316_r110_VTD2024 General.xls',
        'PLANH2316_r110_VTD2024 Primary Election.xls',
        'PLANH2316_r371_VTD2024 General.xls',
        'PLANH2316_r381_VTD2024 General.xls',
    ]
}

for category, files in vtd_files.items():
    print(f"\n{category}:")
    for filename in files:
        exists, size = check_file_exists(filename)
        status = "✓" if exists else "✗"
        print(f"  {status} {filename:<50} {size:>10}")

# Precinct Files (Alternative format)
print("\n[2] Precinct Files (Alternative Format)")
print("-" * 80)

prec_files = {
    'Congressional': [
        'PLANC2333_r365_Prec24G.xls',
        'PLANC2333_r370_Prec24G.xls',
        'PLANC2333_r375_Prec24G.xls',
        'PLANC2333_r380_Prec24G.xls',
    ],
    'State Senate': [
        'PLANS2168_r370_Prec2024 General.xls',
        'PLANS2168_r380_Prec2024 General.xls',
    ],
    'State House': [
        'PLANH2316_r370_Prec2024 General.xls',
        'PLANH2316_r380_Prec2024 General.xls',
    ]
}

for category, files in prec_files.items():
    print(f"\n{category}:")
    for filename in files:
        exists, size = check_file_exists(filename)
        status = "✓" if exists else "✗"
        print(f"  {status} {filename:<50} {size:>10}")

# Shapefiles
print("\n[3] Shapefiles (Geographic Boundaries)")
print("-" * 80)

zip_files = [
    'PLANC2333.zip',
    'PLANC2333_blk.zip',
    'PLANC2333_All_Files.zip',
    'PLANS2168.zip',
    'PLANS2168_blk.zip',
    'PLANS2168_All_Files.zip',
    'PLANH2316.zip',
    'PLANH2316_blk.zip',
    'PLANH2316_All_Files.zip',
]

for zip_file in zip_files:
    exists, size = check_file_exists(zip_file)
    status = "✓" if exists else "✗"
    print(f"  {status} {zip_file:<40} {size:>10}")
    
    if exists:
        contents = analyze_zip_contents(zip_file)
        if contents:
            shp_count = len([f for f in contents if f.endswith('.shp')])
            print(f"      Contains {shp_count} shapefile(s)")

# JSON Reference Files (Already parsed)
print("\n[4] JSON Reference Files (Pre-parsed)")
print("-" * 80)

json_files = [
    'congressional_districts.json',
    'congressional_counties.json',
    'congressional_precincts.json',
    'state_senate_districts.json',
    'state_senate_counties.json',
    'state_house_districts.json',
    'state_house_counties.json',
]

for filename in json_files:
    exists, size = check_file_exists(filename)
    status = "✓" if exists else "✗"
    print(f"  {status} {filename:<50} {size:>10}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

# Count what we have
vtd_count = sum(1 for cat in vtd_files.values() for f in cat if check_file_exists(f)[0])
vtd_total = sum(len(files) for files in vtd_files.values())

prec_count = sum(1 for cat in prec_files.values() for f in cat if check_file_exists(f)[0])
prec_total = sum(len(files) for files in prec_files.values())

zip_count = sum(1 for f in zip_files if check_file_exists(f)[0])
zip_total = len(zip_files)

json_count = sum(1 for f in json_files if check_file_exists(f)[0])
json_total = len(json_files)

print(f"\nVTD Files:       {vtd_count}/{vtd_total} present")
print(f"Precinct Files:  {prec_count}/{prec_total} present")
print(f"Shapefiles:      {zip_count}/{zip_total} present")
print(f"JSON Files:      {json_count}/{json_total} present")

# Critical assessment
print("\n" + "="*80)
print("ASSESSMENT")
print("="*80)

critical_files = [
    'PLANC2333_r110_VTD24G.xls',
    'PLANS2168_r110_VTD2024 General.xls',
    'PLANH2316_r110_VTD2024 General.xls',
]

all_critical_present = all(check_file_exists(f)[0] for f in critical_files)

if all_critical_present:
    print("\n✓ ALL CRITICAL VTD FILES PRESENT")
    print("\nYou have everything needed for precinct-level district assignment:")
    print("  • Congressional districts (PLANC2333)")
    print("  • State Senate districts (PLANS2168)")
    print("  • State House districts (PLANH2316)")
    print("\nNext step: Parse VTD files and build precinct_districts table")
else:
    print("\n✗ MISSING CRITICAL FILES")
    print("\nMissing files:")
    for f in critical_files:
        if not check_file_exists(f)[0]:
            print(f"  • {f}")

# Check for any missing files
print("\n" + "="*80)
print("WHAT'S MISSING (if anything)")
print("="*80)

missing = []
for cat in vtd_files.values():
    for f in cat:
        if not check_file_exists(f)[0]:
            missing.append(f)

for cat in prec_files.values():
    for f in cat:
        if not check_file_exists(f)[0]:
            missing.append(f)

for f in zip_files:
    if not check_file_exists(f)[0]:
        missing.append(f)

for f in json_files:
    if not check_file_exists(f)[0]:
        missing.append(f)

if missing:
    print("\nMissing files:")
    for f in missing:
        print(f"  • {f}")
else:
    print("\n✓ NO FILES MISSING - Complete dataset!")

print("\n" + "="*80)
