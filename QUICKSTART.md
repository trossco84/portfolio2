# Quick Start Guide

Get running in 5 minutes.

## 1. Setup Supabase Database

1. Go to [supabase.com](https://supabase.com)
2. Create a new project (free tier)
3. Copy your connection string from Settings → Database
4. It looks like: `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres`

## 2. Configure Environment

```bash
# Copy example file
cp .env.example .env

# Edit .env and paste your DATABASE_URL
nano .env  # or use your favorite editor
```

## 3. Install & Run

```bash
# Install
pip install -e .

# Run migrations
python portfolio/db/migrations/migrate.py

# Run portfolio for today
python -m portfolio run --asof $(date +%Y-%m-%d) --mode paper

# View reports
ls reports/$(date +%Y-%m-%d)/
cat reports/$(date +%Y-%m-%d)/report.md
```

## 4. View Dashboard

```bash
# Start dashboard
uvicorn app.main:app --reload

# Open browser
open http://localhost:8000
```

## That's it!

Your portfolio is now running. The system will:
- Fetch price data for ~150 stocks/ETFs
- Compute signals for 4 strategies
- Generate target allocations
- Calculate risk metrics
- Produce trade orders
- Save everything to Supabase
- Generate markdown + CSV reports

## Next Steps

- **Schedule weekly runs**: See [README.md](README.md#scheduling)
- **Deploy dashboard**: See [README.md](README.md#deployment-flyio)
- **Customize strategies**: Edit files in `portfolio/strategies/`
- **Add API keys**: Configure Alpaca, News, Reddit in `.env`

## Troubleshooting

**Database error?**
- Check your DATABASE_URL is correct
- Test connection: `psql "your_database_url"`

**No price data?**
- First run takes longer (fetching from yfinance)
- Subsequent runs use cached data
- Ensure internet connection

**Import errors?**
- Reinstall: `pip install -e .`
- Check Python version: `python --version` (need 3.11+)

## Common Commands

```bash
# Run portfolio
make run

# Launch dashboard
make dashboard

# Run tests
make test

# See all commands
make help
```
