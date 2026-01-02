# Weekly Automation Setup

This document explains how to set up weekly automated portfolio reviews with email notifications.

## Overview

The weekly automation workflow:

1. **Syncs positions** from your Alpaca account to the database
2. **Runs portfolio analysis** to generate new recommendations
3. **Calculates rebalance trades** (only if positions drift >15% from target)
4. **Sends email notification** with portfolio stats and recommended trades
5. **Optionally auto-executes** trades (disabled by default for safety)

## Components

### Scripts

- `scripts/sync_positions.py` - Syncs Alpaca positions to database
- `scripts/weekly_review.py` - Main weekly review orchestration
- `scripts/execute_live_trades.py` - Executes trades (manual or auto)

### GitHub Actions Workflow

- `.github/workflows/weekly-review.yml` - Runs every Monday at 9 AM UTC

## Setup

### 1. Local Testing

Test the weekly review locally first:

```bash
cd /Users/trevorross/Desktop/My\ Projects/portfolio2
source venv/bin/activate

# Sync current positions
python scripts/sync_positions.py

# Run weekly review
python scripts/weekly_review.py
```

This will:
- Fetch your current Alpaca positions
- Run portfolio analysis
- Calculate recommended trades
- Save email report to `reports/[DATE]/weekly_email.txt`

### 2. Email Configuration

The system supports SendGrid for email delivery. To enable:

#### Option A: SendGrid (Recommended)

1. Sign up for SendGrid free tier (100 emails/day): https://sendgrid.com
2. Create an API key
3. Add to `.env`:

```bash
# Email configuration
EMAIL_FROM=your-portfolio@yourdomain.com
EMAIL_TO=your-email@gmail.com
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Dashboard URL for email links
DASHBOARD_URL=https://your-app.fly.dev
```

4. Install SendGrid dependency:

```bash
pip install sendgrid
```

#### Option B: No Email (Testing)

If you don't configure email, the system will:
- Print the email content to console
- Save it to `reports/[DATE]/weekly_email.txt`
- Continue running normally

### 3. GitHub Actions Setup

To run weekly reviews automatically via GitHub Actions:

#### Set Repository Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions

Add these secrets:

```
DATABASE_URL=postgresql://...
ALPACA_API_KEY=AKJEJJEWNXLYVZFABCL54LUHX3
ALPACA_SECRET_KEY=4fuC2qiYBN6arsAJAqDanT8mstkcs63nTU3fpAj73oay
ALPACA_PAPER=false
TOTAL_CAPITAL=10000
CASH_RESERVE=2000
SLEEVE_CAPITAL=2000
EMAIL_TO=your-email@gmail.com
EMAIL_FROM=portfolio@yourdomain.com
SENDGRID_API_KEY=SG.xxxxxxxxxxxx
```

#### Schedule

The workflow runs:
- **Every Monday at 9 AM UTC** (1 AM PST / 4 AM EST)
- **Or manually** via GitHub Actions UI

To change the schedule, edit `.github/workflows/weekly-review.yml`:

```yaml
on:
  schedule:
    # Cron format: minute hour day month weekday
    - cron: '0 9 * * 1'  # Every Monday 9 AM UTC
```

Examples:
- `'0 14 * * 1'` - Every Monday 2 PM UTC (9 AM EST)
- `'0 9 * * 2'` - Every Tuesday 9 AM UTC
- `'0 9 1 * *'` - First day of every month

## Email Report Format

The weekly email includes:

```
📊 WEEKLY PORTFOLIO REVIEW - 2025-01-06

================================================================================
PORTFOLIO SUMMARY
================================================================================

Total Value:  $3,245.67
Cash:         $250.00
Invested:     $2,995.67

================================================================================
RISK METRICS
================================================================================

Beta (vs SPY):        0.78
Volatility (annual):  18.06%
Sharpe Ratio:         2.55
Max Drawdown:         -17.84%

================================================================================
HOLDINGS BY SLEEVE
================================================================================

FUTURISTIC        6 positions  $   856.86
MOMENTUM          6 positions  $ 1,042.77
REALWORLD        11 positions  $ 1,091.23

================================================================================
RECOMMENDED TRADES (3)
================================================================================

BUY    TSLA       2 shares - Increase (drift: 18.2%)
SELL   AMD        1 shares - Reduce (drift: 22.5%)
BUY    MO         1 shares - New position

💡 Rebalancing threshold: Positions drifted >15% from target

🔗 View Dashboard: https://your-app.fly.dev
```

## Rebalancing Strategy

**Conservative long-term approach:**

- Only rebalances if positions drift **>15%** from target
- No trades if portfolio is well-balanced
- Typical frequency: 0-3 trades per week (often zero)
- Minimizes transaction costs and tax implications

### When Trades Are Recommended

1. **New positions** - Strategy adds a new ticker
2. **Exits** - Strategy removes a ticker
3. **Drift >15%** - Position grew/shrunk significantly vs target

### When NO Trades Are Recommended

- All positions within 15% of target
- Portfolio is balanced
- Email will say "No rebalancing needed"

## Auto-Execution (Optional)

**By default, trades are NOT auto-executed** for safety.

To enable auto-execution:

1. Edit `scripts/weekly_review.py`:

```python
# Step 5: Auto-execute (if enabled)
auto_execute = True  # Change from False to True
```

2. Trades will still require confirmation:
   - You'll be prompted to type 'YES'
   - Only runs interactively (not in GitHub Actions)

**For fully automated trading:**

Remove the confirmation prompt in `weekly_review.py`. Only do this if you're comfortable with fully automated trading.

## Dashboard Updates

The weekly review automatically updates your dashboard:

1. Syncs latest positions from Alpaca
2. Calculates current portfolio stats
3. Updates database with new run
4. Dashboard at `http://localhost:8000` (or Fly.io URL) shows latest data

## Monitoring

### GitHub Actions

- View workflow runs: GitHub repo → Actions tab
- Download reports: Each run uploads artifacts (90 day retention)
- Failures create GitHub issues automatically

### Local Logs

- Email reports: `reports/[DATE]/weekly_email.txt`
- Portfolio reports: `reports/[DATE]/report.md`
- Trade orders: `reports/[DATE]/orders.csv`

## Manual Execution

You can always run the weekly review manually:

```bash
# Full review
python scripts/weekly_review.py

# Just sync positions
python scripts/sync_positions.py

# Execute recommended trades
python scripts/execute_live_trades.py
```

## Troubleshooting

### No Email Received

1. Check SendGrid dashboard for send status
2. Verify `EMAIL_TO` is correct
3. Check spam folder
4. Review GitHub Actions logs

### Trades Not Executing

- Auto-execution is disabled by default
- Check that `auto_execute = True` in script
- Verify Alpaca API keys are correct
- Check Alpaca account has buying power

### Portfolio Analysis Failed

- Verify database connection
- Check yfinance is working
- Review error logs in GitHub Actions

## Cost

- **GitHub Actions**: Free (within limits)
- **SendGrid**: Free tier (100 emails/day)
- **Supabase**: Free tier sufficient
- **Total**: $0/month for automation

## Summary

Once set up, you'll receive:
- **Weekly email** every Monday with portfolio stats
- **Trade recommendations** only when needed (>15% drift)
- **Dashboard access** anytime at your URL
- **Full automation** with GitHub Actions
- **Manual control** over trade execution

Conservative, long-term focused, low-maintenance portfolio management.
