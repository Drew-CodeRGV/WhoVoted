#!/bin/bash
# Setup McAllen ISD Bond 2026 section

set -e

echo "========================================"
echo "McAllen ISD Bond 2026 - Setup"
echo "========================================"

cd /opt/whovoted

# Create directory if it doesn't exist
mkdir -p public/misdbond2026

# Restart Flask to load new API routes
echo "Restarting Flask..."
sudo systemctl restart whovoted

echo ""
echo "✓ Setup complete"
echo ""
echo "Access at: https://politiquera.com/misdbond2026/"
echo ""
echo "To import rosters, run:"
echo "  python3 deploy/import_misdbond2026_roster.py"
