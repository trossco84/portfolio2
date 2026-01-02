# 🎉 Weekly Automation Setup Complete!

Your portfolio system now has full weekly automation with email notifications and optional auto-execution.

## What's Been Set Up

### ✅ Position Syncing
- **Script**: `scripts/sync_positions.py`
- **Purpose**: Syncs your live Alpaca positions to the database
- **Updates**: Dashboard with current holdings

### ✅ Weekly Review
- **Script**: `scripts/weekly_review.py`
- **Purpose**: Comprehensive weekly portfolio analysis
- **Includes**:
  - Current portfolio value and P/L
  - Risk metrics (beta, volatility, Sharpe, drawdown)
  - Holdings breakdown by sleeve
  - Conservative rebalance recommendations (only if >15% drift)

### ✅ Email Notifications
- **Module**: `portfolio/notifications.py`
- **Provider**: SendGrid (optional)
- **Content**: Full weekly summary with dashboard link
- **Fallback**: Saves to file if email not configured

### ✅ GitHub Actions Workflow
- **File**: `.github/workflows/weekly-review.yml`
- **Schedule**: Every Monday at 9 AM UTC (1 AM PST / 4 AM EST)
- **Features**:
  - Automated weekly runs
  - Report artifacts (90 day retention)
  - Auto-creates issues on failure

### ✅ Live Trade Execution
- **Script**: `scripts/execute_live_trades.py`
- **Already tested**: You successfully executed 23 trades today!
- **Safety**: Requires typing "EXECUTE" to confirm
- **Smart sizing**: Adjusts quantities to fit available capital

## Quick Start

### Test Locally (Recommended First)

```bash
cd /Users/trevorross/Desktop/My\ Projects/portfolio2
source venv/bin/activate

# 1. Sync your current positions
python scripts/sync_positions.py

# 2. Run weekly review
python scripts/weekly_review.py
```

**Output**:
- Console: Full summary of portfolio stats and trades
- File: `reports/[DATE]/weekly_email.txt`
- Dashboard: Updated at http://localhost:8000

### Enable Email (Optional)

1. **Sign up for SendGrid free tier**: https://sendgrid.com/free/
   - 100 emails/day free
   - No credit card required

2. **Get API key**:
   - SendGrid Dashboard → Settings → API Keys
   - Create new key with "Mail Send" permission

3. **Add to .env**:
```bash
EMAIL_FROM=portfolio@yourdomain.com
EMAIL_TO=your-email@gmail.com
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHBOARD_URL=http://localhost:8000  # or your Fly.io URL
```

4. **Install SendGrid**:
```bash
pip install sendgrid
```

5. **Test**:
```bash
python scripts/weekly_review.py
# Check your inbox!
```

### Set Up GitHub Actions

1. **Push to GitHub**:
```bash
git add .
git commit -m "Add weekly automation"
git push
```

2. **Add Secrets**:
   - Go to: GitHub repo → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Add each secret from your `.env` file:

   ```
   DATABASE_URL
   ALPACA_API_KEY
   ALPACA_SECRET_KEY
   ALPACA_PAPER
   TOTAL_CAPITAL
   CASH_RESERVE
   SLEEVE_CAPITAL
   EMAIL_TO
   EMAIL_FROM
   SENDGRID_API_KEY
   DASHBOARD_URL
   ```

3. **Test Workflow**:
   - Go to: Actions tab
   - Select "Weekly Portfolio Review"
   - Click "Run workflow"
   - Check your email in ~2 minutes

## What You'll Receive Weekly

Every Monday morning, you'll get an email like this:

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
RECOMMENDED TRADES (2)
================================================================================

BUY    TSLA       1 shares - Increase (drift: 18.2%)
SELL   AMD        1 shares - Reduce (drift: 22.5%)

💡 Rebalancing threshold: Positions drifted >15% from target

🔗 View Dashboard: https://your-app.fly.dev
```

## Rebalancing Philosophy

**Conservative, long-term approach:**

- ✅ Only rebalances when positions drift **>15%** from target
- ✅ Typically **0-3 trades per week** (often zero)
- ✅ Minimizes transaction costs and tax implications
- ✅ Focuses on **buy and hold** with periodic adjustments
- ✅ **Manual approval** required for trade execution (safety first)

**When trades ARE recommended:**
- New ticker added to strategy
- Ticker removed from strategy
- Position drifted >15% from target (price movement)

**When trades are NOT recommended:**
- Portfolio well-balanced
- All positions within 15% of target
- Email will say "No rebalancing needed"

## Auto-Execution (Optional)

By default, **trades require manual execution** for safety.

To execute recommended trades:

```bash
# After receiving weekly email with trade recommendations
python scripts/execute_live_trades.py

# Or manually review allocations in dashboard
open http://localhost:8000
```

**To enable auto-execution** (advanced):
1. Edit `scripts/weekly_review.py`
2. Change `auto_execute = False` to `auto_execute = True`
3. Add confirmation logic or remove for fully automated trading

⚠️ **Only enable auto-execution if you're comfortable with fully automated trading!**

## Monitoring

### Dashboard
- **URL**: http://localhost:8000 (or your Fly.io URL)
- **Updated**: Automatically after each weekly run
- **Shows**: Current positions, allocations, risk metrics, P/L

### GitHub Actions
- **View runs**: GitHub repo → Actions tab
- **Artifacts**: Download reports from each run (90 days)
- **Failures**: Auto-creates GitHub issue

### Email
- **Frequency**: Every Monday 9 AM UTC
- **Content**: Full portfolio summary + trade recommendations
- **Archive**: Saved to `reports/[DATE]/weekly_email.txt`

## Customize Schedule

Edit `.github/workflows/weekly-review.yml`:

```yaml
schedule:
  # Cron: minute hour day month weekday
  - cron: '0 9 * * 1'  # Every Monday 9 AM UTC
```

**Examples:**
- `'0 14 * * 1'` - Every Monday 2 PM UTC (9 AM EST)
- `'0 9 * * 5'` - Every Friday 9 AM UTC
- `'0 9 1 * *'` - First day of every month

## Cost Breakdown

| Service | Usage | Cost |
|---------|-------|------|
| GitHub Actions | Weekly runs | Free |
| SendGrid | Email notifications | Free (100/day) |
| Supabase | Database | Free tier |
| Fly.io | Dashboard | $0-3/month |
| **Total** | | **~$0-3/month** |

## Files Created

```
scripts/
  sync_positions.py          # Sync Alpaca positions
  weekly_review.py           # Main weekly orchestration
  execute_live_trades.py     # Live trade execution

portfolio/
  notifications.py           # Email delivery

.github/workflows/
  weekly-review.yml         # GitHub Actions automation

.env.example                 # Config template
WEEKLY_AUTOMATION.md        # Full documentation
SETUP_COMPLETE.md           # This file
```

## Next Steps

1. ✅ **Test locally** - Run `python scripts/weekly_review.py`
2. ⬜ **Set up email** - Add SendGrid API key to `.env`
3. ⬜ **Configure GitHub Actions** - Add secrets to GitHub repo
4. ⬜ **Test workflow** - Manually trigger in Actions tab
5. ⬜ **Wait for Monday** - Receive your first automated email!

## Support

- **Full docs**: See `WEEKLY_AUTOMATION.md`
- **Configuration**: See `.env.example`
- **Troubleshooting**: Check GitHub Actions logs

## Summary

You now have a fully automated weekly portfolio review system that:

- 📊 Analyzes your portfolio every Monday
- 📧 Sends you comprehensive email updates
- 🎯 Recommends trades only when needed (>15% drift)
- 🔒 Requires manual approval for safety
- 💰 Costs ~$0/month to run
- 🤖 Fully automated via GitHub Actions

**Your portfolio is on autopilot!** 🚀

Just check your email every Monday, review the recommendations, and execute trades if needed. The system handles everything else.
