#!/bin/bash
# Fix CPct-2 to match certified numbers exactly

set -e

echo "========================================"
echo "CPCT-2 EXACT FIX"
echo "========================================"
echo ""
echo "Target: 9,876 early + 3,754 election day = 13,630 DEM"
echo ""

cd /opt/whovoted

echo "Step 1: Reverse engineer correct precinct list..."
python3 deploy/reverse_engineer_cpct2_from_certified.py

echo ""
echo "Step 2: Apply correct precincts and update boundary..."
python3 deploy/apply_cpct2_correct_precincts.py

echo ""
echo "Step 3: Regenerate CPct-2 report cache..."
python3 deploy/regenerate_cpct2_report.py

echo ""
echo "========================================"
echo "COMPLETE"
echo "========================================"
echo ""
echo "Check the results at:"
echo "https://politiquera.com/reports.html?district=CPct-2"
