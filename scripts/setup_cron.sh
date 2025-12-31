#!/bin/bash
# Setup cron job for weekly portfolio runs
# Usage: ./scripts/setup_cron.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up weekly cron job for portfolio runs..."
echo "Project directory: $PROJECT_DIR"

# Create cron job entry
CRON_JOB="0 9 * * 1 cd $PROJECT_DIR && python scripts/run_weekly.py >> $PROJECT_DIR/logs/cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_weekly.py"; then
    echo "Cron job already exists. Skipping..."
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job added successfully!"
    echo "Schedule: Every Monday at 9 AM"
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

echo ""
echo "Current crontab:"
crontab -l

echo ""
echo "Done! Portfolio will run every Monday at 9 AM."
echo "Logs will be written to: $PROJECT_DIR/logs/cron.log"
