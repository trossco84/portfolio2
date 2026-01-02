#!/bin/bash
#
# Test the weekly review workflow locally
#

set -e

echo "=================================="
echo "TESTING WEEKLY REVIEW WORKFLOW"
echo "=================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate venv
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "ERROR: venv not found. Run ./scripts/init_project.sh first"
    exit 1
fi

# Check environment
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found"
    exit 1
fi

echo "✓ Environment ready"
echo ""

# Step 1: Sync positions
echo "📊 Step 1: Syncing Alpaca positions..."
python scripts/sync_positions.py

echo ""
echo "Press Enter to continue to weekly review..."
read

# Step 2: Weekly review
echo "📈 Step 2: Running weekly review..."
python scripts/weekly_review.py

echo ""
echo "=================================="
echo "TEST COMPLETE"
echo "=================================="
echo ""
echo "Check:"
echo "  - Console output above for summary"
echo "  - reports/$(date +%Y-%m-%d)/weekly_email.txt for email preview"
echo "  - http://localhost:8000 for dashboard (if running)"
echo ""
