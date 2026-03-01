#!/bin/bash
# Master optimization script - runs all steps in correct order
# Safe to run multiple times (idempotent)

set -e  # Exit on error

PYTHON="/opt/whovoted/venv/bin/python3"
DEPLOY_DIR="/opt/whovoted/deploy"
DB_PATH="/opt/whovoted/data/whovoted.db"
BACKUP_PATH="/opt/whovoted/data/whovoted.db.backup.$(date +%Y%m%d_%H%M%S)"

echo "========================================================================"
echo "WhoVoted Performance Optimization - Master Script"
echo "========================================================================"
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found: $DB_PATH"
    exit 1
fi

# Create backup
echo "Creating backup..."
cp "$DB_PATH" "$BACKUP_PATH"
echo "✓ Backup created: $BACKUP_PATH"
echo ""

# Step 1: Add indexes (fast, safe, huge impact)
echo "========================================================================"
echo "STEP 1: Adding Database Indexes"
echo "========================================================================"
$PYTHON "$DEPLOY_DIR/optimize_step1_indexes.py"
if [ $? -ne 0 ]; then
    echo "❌ Step 1 failed"
    exit 1
fi
echo ""

# Step 2: Add computed columns (safe, one-time, 10-50x speedup)
echo "========================================================================"
echo "STEP 2: Adding Computed Columns (Denormalization)"
echo "========================================================================"
echo "This will add computed columns for fast queries."
echo "Original data will NOT be modified."
echo ""
echo "Continue? (yes/no): "
read -r response
if [ "$response" != "yes" ]; then
    echo "Skipping denormalization."
else
    $PYTHON "$DEPLOY_DIR/optimize_safe_denormalization.py" <<< "yes"
    if [ $? -ne 0 ]; then
        echo "❌ Step 2 failed - restoring backup"
        cp "$BACKUP_PATH" "$DB_PATH"
        exit 1
    fi
fi
echo ""

# Step 3: Pre-compute gazette (slow, but only needs to run after scraper)
echo "========================================================================"
echo "STEP 3: Pre-computing Gazette Insights"
echo "========================================================================"
echo "This may take 2-5 minutes..."
$PYTHON "$DEPLOY_DIR/optimize_step2_gazette.py"
if [ $? -ne 0 ]; then
    echo "⚠️  Step 3 failed - gazette will compute on-demand (slower)"
fi
echo ""

# Done
echo "========================================================================"
echo "✅ Optimization Complete!"
echo "========================================================================"
echo ""
echo "Backup saved to: $BACKUP_PATH"
echo ""
echo "Next steps:"
echo "  1. Restart app: sudo supervisorctl restart whovoted"
echo "  2. Test household popup (should be <1s)"
echo "  3. Test gazette (should load instantly)"
echo "  4. Test district campaigns (should be fast)"
echo ""
echo "To rollback (if needed):"
echo "  cp $BACKUP_PATH $DB_PATH"
echo "  sudo supervisorctl restart whovoted"
echo ""
