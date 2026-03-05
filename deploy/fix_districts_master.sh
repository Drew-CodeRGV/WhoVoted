#!/bin/bash
# Master script to fix district assignments
# Run each step in sequence, stopping if any step fails

set -e  # Exit on error

echo "================================================================================"
echo "DISTRICT ACCURACY FIX - MASTER EXECUTION SCRIPT"
echo "================================================================================"
echo ""
echo "This will run all 6 steps to fix district assignments:"
echo "  1. Diagnose - Identify errors"
echo "  2. Acquire - Download boundaries"
echo "  3. Validate - Test assignment logic"
echo "  4. Rebuild - Regenerate assignments"
echo "  5. Verify - Confirm accuracy"
echo "  6. Prevent - Add safeguards"
echo ""
echo "⚠️  WARNING: Step 4 will modify the database"
echo ""
read -p "Do you want to proceed? (yes/no): " response

if [ "$response" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

cd /opt/whovoted
source venv/bin/activate

echo ""
echo "================================================================================"
echo "STEP 1: DIAGNOSE"
echo "================================================================================"
python3 deploy/verify_districts_step1_diagnose.py
if [ $? -ne 0 ]; then
    echo "✗ Step 1 failed"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 2: ACQUIRE"
echo "================================================================================"
python3 deploy/verify_districts_step2_acquire.py
if [ $? -ne 0 ]; then
    echo "✗ Step 2 failed"
    exit 1
fi

# Check if required files exist
if [ ! -f "data/tx_congressional_2023.geojson" ]; then
    echo "✗ Missing required file: data/tx_congressional_2023.geojson"
    echo "  Download this file manually and re-run"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 3: VALIDATE"
echo "================================================================================"
python3 deploy/verify_districts_step3_validate.py
if [ $? -ne 0 ]; then
    echo "✗ Step 3 failed"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 4: REBUILD"
echo "================================================================================"
echo "⚠️  About to modify database..."
python3 deploy/verify_districts_step4_rebuild.py
if [ $? -ne 0 ]; then
    echo "✗ Step 4 failed"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 5: VERIFY"
echo "================================================================================"
python3 deploy/verify_districts_step5_verify.py
if [ $? -ne 0 ]; then
    echo "✗ Step 5 failed - verification errors found"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 6: PREVENT"
echo "================================================================================"
python3 deploy/verify_districts_step6_prevent.py
if [ $? -ne 0 ]; then
    echo "✗ Step 6 failed"
    exit 1
fi

echo ""
echo "================================================================================"
echo "ALL STEPS COMPLETE"
echo "================================================================================"
echo ""
echo "✓ District assignments have been fixed"
echo ""
echo "Next steps:"
echo "  1. Regenerate cached reports: python3 deploy/regenerate_district_cache_complete.py"
echo "  2. Test campaign reports"
echo "  3. Deploy to production"
