# Monthly Portfolio Deep-Dive

## Overview

Every **first Monday of the month**, an enhanced portfolio review runs automatically with:
- 📰 News analysis for all holdings (past 30 days)
- 💹 Analyst sentiment & price targets
- 🤖 AI-powered comprehensive analysis
- 📊 Strategic recommendations

This complements the weekly review with deeper insights and market context.

## What's Different from Weekly Reviews?

| Feature | Weekly Review | Monthly Deep-Dive |
|---------|--------------|-------------------|
| **Frequency** | Every Monday | First Monday only |
| **News** | ❌ No | ✅ Yes (30 days) |
| **Analyst Data** | ❌ No | ✅ Yes |
| **AI Analysis** | Basic (4-6 sentences) | Comprehensive (10-15 sentences) |
| **Focus** | Rebalancing | Strategic insights |
| **Runtime** | ~2-3 min | ~4-6 min |
| **Cost** | ~$0.02 | ~$0.05 |

## Email Content

Monthly emails include:

1. **Portfolio Summary** - NAV, cash, sleeve breakdown
2. **30-Day Risk Metrics** - Sharpe, beta, volatility, drawdown
3. **AI Analysis** - Comprehensive review covering:
   - Portfolio health & performance
   - Sleeve balance assessment
   - Position-level insights with news context
   - Market sentiment analysis
   - Strategic recommendations
   - Risk assessment

4. **Top News Highlights** - Top 10 news stories affecting your holdings
5. **Dashboard Link** - Live portfolio view

## Example Analysis

```
Portfolio maintains strong risk-adjusted returns with a Sharpe ratio of 2.54,
though the 102.7% invested position leaves minimal flexibility for opportunistic
deployment. The heavy concentration in the futuristic sleeve (8/11 positions,
39.4% of NAV) creates sector-specific risk, particularly given recent volatility
in semiconductor and AI-related stocks.

Recent news for PLTR highlights continued government contract wins, supporting
the current position, while MU faces headwinds from datacenter inventory
normalization based on analyst downgrades this month. The momentum sleeve is
significantly underweight with only 3 positions worth $171 (5.8% vs target
allocation).

Key recommendations: 1) Rebalance to meet sleeve targets by rotating some gains
from futuristic into momentum strategy, 2) Build cash reserves to 5-10% for
tactical opportunities, 3) Consider trimming semiconductor exposure given
concentration risk and mixed near-term outlook.
```

## GitHub Workflow

File: [.github/workflows/monthly-review.yml](.github/workflows/monthly-review.yml)

**Trigger**: First Monday of each month at 10 AM UTC (2 AM PST / 5 AM EST)

**What it does**:
1. Checks if it's the first Monday (days 1-7)
2. Fetches news for all holdings (past 30 days)
3. Collects analyst sentiment & price targets
4. Runs AI analysis with full context
5. Sends comprehensive email report
6. Uploads report artifact (1-year retention)

## Manual Execution

You can run the monthly review anytime:

```bash
# Run locally
python scripts/monthly_review.py

# Run via GitHub Actions
Go to Actions → Monthly Portfolio Deep-Dive → Run workflow
```

## Cost & Resources

**API Usage**:
- News fetching: Free (yfinance)
- Analyst data: Free (yfinance)
- AI analysis: ~$0.05/month (Claude 3.5 Sonnet with 3K tokens)

**Total Monthly Cost**: ~$0.05

**GitHub Actions**:
- Runtime: ~4-6 minutes
- Free tier: 2,000 minutes/month
- Monthly usage: ~6 min (well within limits)

## Fallback Behavior

If AI or news APIs are unavailable, the system provides:
- Quantitative portfolio analysis
- Sleeve distribution breakdown
- Top 5 position concentration analysis
- Rule-based recommendations

The email still sends successfully with useful insights.

## Configuration

### Required Secrets (Already Set)

Same as weekly review:
- `DATABASE_URL`
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`
- `EMAIL_TO` / `EMAIL_FROM` / `SENDGRID_API_KEY`
- `ANTHROPIC_API_KEY` (for AI analysis)

### No Additional Setup Needed!

The monthly workflow uses the same secrets as your weekly review.

## Next Monthly Review

Check the GitHub Actions tab to see when the next monthly review is scheduled.

**To test now**: Go to Actions → Monthly Portfolio Deep-Dive → Run workflow

## Customization

Want to adjust the monthly review?

**Change frequency**: Edit `.github/workflows/monthly-review.yml` cron schedule
**Change news lookback**: Edit `scripts/monthly_review.py` line 61 (`days=30`)
**Change AI model**: Edit `portfolio/ai/monthly_analysis.py` line 52
**Add more analysis**: Extend `monthly_analyzer.analyze_with_news()` prompt

## Files

- **Workflow**: [.github/workflows/monthly-review.yml](.github/workflows/monthly-review.yml)
- **Script**: [scripts/monthly_review.py](scripts/monthly_review.py)
- **News Module**: [portfolio/data/news.py](portfolio/data/news.py)
- **AI Analysis**: [portfolio/ai/monthly_analysis.py](portfolio/ai/monthly_analysis.py)

---

**Your portfolio now has automated weekly check-ins AND monthly deep-dives!** 🚀
