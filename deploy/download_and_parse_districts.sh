#!/bin/bash
# Download district reference files directly from Texas Legislature and parse them
set -e

echo "================================================================================"
echo "DOWNLOAD AND PARSE DISTRICT REFERENCE FILES"
echo "================================================================================"
echo ""

cd /home/ubuntu/WhoVoted/data/district_reference

# Install dependencies
echo "Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y unzip wget
pip install -q pandas xlrd openpyxl

echo ""
echo "================================================================================"
echo "DOWNLOADING FILES FROM TEXAS LEGISLATURE"
echo "================================================================================"
echo ""

# Congressional Districts (PLANC2333)
echo "Downloading Congressional Districts (PLANC2333)..."
wget -q --show-progress -O PLANC2333_All_Files.zip \
  "https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/fb6d5523-8ee2-40bd-97b6-256c42802060/download/planc2333_all_files_20251009.zip"

# State Senate Districts (PLANS2168)
echo "Downloading State Senate Districts (PLANS2168)..."
wget -q --show-progress -O PLANS2168_All_Files.zip \
  "https://data.capitol.texas.gov/dataset/70836384-f10c-423d-a36e-748d7e000872/resource/782ff71d-5c67-4bf5-bf05-7accfbb107a2/download/plans2168_all_files_20250220.zip"

# State House Districts (PLANH2316)
echo "Downloading State House Districts (PLANH2316)..."
wget -q --show-progress -O PLANH2316_All_Files.zip \
  "https://data.capitol.texas.gov/dataset/71af633c-21bf-42cf-ad48-4fe95593a897/resource/b54d618c-c129-4f19-a52c-b207e9f37a79/download/planh2316_all_files_20250220.zip"

echo ""
echo "✓ All files downloaded"
echo ""

# Show downloaded files
echo "Downloaded files:"
ls -lh *All_Files*.zip

echo ""
echo "================================================================================"
echo "EXTRACTING FILES"
echo "================================================================================"
echo ""

# Extract all ZIP files
for zipfile in *All_Files*.zip; do
    if [ -f "$zipfile" ]; then
        echo "Extracting $zipfile..."
        unzip -o -q "$zipfile"
        echo "  ✓ Done"
    fi
done

echo ""
echo "Extraction complete!"
echo ""

# Count extracted files
echo "================================================================================"
echo "EXTRACTED FILES SUMMARY"
echo "================================================================================"
xls_count=$(ls -1 *.xls 2>/dev/null | wc -l)
pdf_count=$(ls -1 *.pdf 2>/dev/null | wc -l)
shp_count=$(ls -1 *.shp 2>/dev/null | wc -l)

echo "  XLS files: $xls_count"
echo "  PDF files: $pdf_count"
echo "  Shapefiles: $shp_count"
echo ""

# Show sample XLS files
echo "Sample XLS files:"
ls -lh *.xls 2>/dev/null | head -10

echo ""
echo "================================================================================"
echo "RUNNING PARSER"
echo "================================================================================"
echo ""

cd /home/ubuntu/WhoVoted

# Run parser
python deploy/parse_district_files.py

echo ""
echo "================================================================================"
echo "VERIFICATION"
echo "================================================================================"
echo ""

# Check JSON files
echo "Generated JSON files:"
ls -lh data/district_reference/*.json 2>/dev/null

echo ""
echo "District counts:"
python3 -c "import json; f=open('data/district_reference/congressional_counties.json'); d=json.load(f); print('  Congressional:', len(d), 'districts')" 2>/dev/null || echo "  Congressional: Not found"
python3 -c "import json; f=open('data/district_reference/state_senate_counties.json'); d=json.load(f); print('  State Senate:', len(d), 'districts')" 2>/dev/null || echo "  State Senate: Not found"
python3 -c "import json; f=open('data/district_reference/state_house_counties.json'); d=json.load(f); print('  State House:', len(d), 'districts')" 2>/dev/null || echo "  State House: Not found"

echo ""
echo "================================================================================"
echo "COMPLETE!"
echo "================================================================================"
echo ""
echo "All district reference files have been:"
echo "  ✓ Downloaded from Texas Legislature"
echo "  ✓ Extracted from ZIP files"
echo "  ✓ Parsed into JSON files"
echo ""
echo "The system can now reference these files for accurate district data!"
echo ""
