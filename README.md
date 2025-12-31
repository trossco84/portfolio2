# Multi-Strategy Portfolio Manager

A production-ready, long-only, multi-strategy algorithmic portfolio management system with risk analytics and a lightweight web dashboard.

## Overview

Manages a $25K portfolio split into:
- **$5K Cash Reserve** (not traded)
- **$5K Momentum Sleeve** - Price momentum + sentiment (monthly rebalance)
- **$5K Futuristic Sleeve** - Robotics, AI, nuclear themes (quarterly rebalance)
- **$5K Real-World Sleeve** - Industrials, staples, resilient cash flow (semi-annual rebalance)
- **$5K Risk/Hedge Sleeve** - ETF-based portfolio optimization (weekly rebalance)

### Key Features

- ✅ Clean architecture with modular strategies
- ✅ Postgres (Supabase) persistence layer
- ✅ Risk analytics: beta, volatility, Sharpe ratio, drawdown, correlation
- ✅ Portfolio optimization with efficient frontier (cvxpy optional)
- ✅ Paper trading + Alpaca integration
- ✅ FastAPI dashboard with real-time metrics
- ✅ CLI interface for automation
- ✅ Comprehensive reporting (Markdown + CSV)
- ✅ GitHub Actions CI/CD + scheduled runs
- ✅ Fly.io deployment ready

## Quick Start

### Prerequisites

- Python 3.11+
- Supabase account (free tier works)
- Optional: Alpaca API account for live execution
- Optional: News/Reddit API keys for sentiment

### 1. Installation

```bash
# Clone repository
cd portfolio2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Install optional optimizer
pip install -e ".[optimizer]"

# Install dev dependencies for testing
pip install -e ".[dev]"
```

### 2. Database Setup (Supabase)

#### Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a free project
2. Get your connection string:
   - Go to Project Settings → Database
   - Copy the "Connection string" under "Connection pooling"
   - Format: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

#### Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set DATABASE_URL
# DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

#### Run Migrations

```bash
python portfolio/db/migrations/migrate.py
```

This creates all tables and seeds initial state.

### 3. Run Portfolio

```bash
# Run portfolio optimization for today (paper mode)
python -m portfolio run --asof 2025-12-26 --mode paper

# Check outputs
ls reports/2025-12-26/
# report.md  orders.csv
```

### 4. Launch Dashboard

```bash
# Start FastAPI dashboard
uvicorn app.main:app --reload

# Open browser to http://localhost:8000
```

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Database (REQUIRED)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Portfolio Configuration
TOTAL_CAPITAL=25000
CASH_RESERVE=5000
SLEEVE_CAPITAL=5000

# Optional: Alpaca API (for live trading)
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_PAPER=true

# Optional: Sentiment APIs
NEWS_API_KEY=your_news_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret

# Optional: Dashboard Authentication
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=secure_password

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Trading Constraints

Modify in `portfolio/config.py`:

- `min_trade_size`: Minimum trade size ($50 default)
- `max_position_pct`: Max position size per sleeve (20% default)

### Strategy Universes

Edit static universes in `portfolio/data/universes.py`:

- `MOMENTUM_UNIVERSE`: Large cap growth stocks
- `FUTURISTIC_UNIVERSE`: Robotics, AI, nuclear
- `REALWORLD_UNIVERSE`: Industrials, staples, utilities
- `RISK_UNIVERSE`: ETFs for optimization

## CLI Usage

### Run Portfolio

```bash
# Run for specific date
python -m portfolio run --asof 2025-12-26 --mode paper

# Run for today
python -m portfolio run --asof $(date +%Y-%m-%d) --mode paper

# Live mode (requires Alpaca API)
python -m portfolio run --asof 2025-12-26 --mode live
```

### Generate Report

```bash
# Regenerate report for existing run
python -m portfolio report --asof 2025-12-26
```

## Scheduling

### Option 1: GitHub Actions (Recommended)

The repository includes a workflow that runs weekly:

1. Push code to GitHub
2. Add secrets to repository:
   - `DATABASE_URL`
   - `ALPACA_API_KEY` (optional)
   - `ALPACA_SECRET_KEY` (optional)
   - `NEWS_API_KEY` (optional)
   - `REDDIT_CLIENT_ID` (optional)
   - `REDDIT_CLIENT_SECRET` (optional)

3. Enable GitHub Actions in repository settings
4. The workflow runs every Monday at 9 AM UTC

See [.github/workflows/weekly_run.yml](.github/workflows/weekly_run.yml)

### Option 2: Cron (Local)

```bash
# Setup cron job (runs every Monday at 9 AM)
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh

# Or manually add to crontab:
crontab -e
# Add: 0 9 * * 1 cd /path/to/portfolio2 && python scripts/run_weekly.py
```

## Deployment (Fly.io)

### Deploy Dashboard

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch app (first time)
fly launch --config fly.toml

# Set secrets
fly secrets set DATABASE_URL="postgresql://..."
fly secrets set DASHBOARD_USERNAME="admin"
fly secrets set DASHBOARD_PASSWORD="your_password"

# Deploy
fly deploy

# Check status
fly status

# View logs
fly logs
```

### Cost

Using the cheapest configuration (256MB RAM, shared CPU, auto-stop):
- **~$0-3/month** (scales to zero when idle)

### Update Deployment

```bash
# After code changes
fly deploy
```

## Project Structure

```
portfolio2/
├── portfolio/              # Core package
│   ├── cli.py             # CLI interface
│   ├── config.py          # Configuration
│   ├── db/                # Database layer
│   │   ├── client.py      # Postgres client
│   │   ├── models.py      # Pydantic schemas
│   │   ├── repo.py        # Data access layer
│   │   └── migrations/    # SQL migrations
│   ├── data/              # Data fetchers
│   │   ├── prices.py      # yfinance integration
│   │   ├── sentiment.py   # News/Reddit stubs
│   │   └── universes.py   # Static ticker lists
│   ├── strategies/        # Strategy modules
│   │   ├── momentum/      # Momentum strategy
│   │   ├── futuristic/    # Futuristic strategy
│   │   ├── realworld/     # Real-world strategy
│   │   └── risk/          # Risk/hedge strategy
│   ├── risk/              # Risk analytics
│   │   └── analytics.py   # Risk metrics engine
│   ├── optimizer/         # Portfolio optimization
│   │   └── trade_plan.py  # Trade plan generator
│   ├── execution/         # Order execution
│   │   ├── paper_broker.py
│   │   └── alpaca_broker.py
│   ├── reporting/         # Report generation
│   │   └── generator.py
│   └── utils/             # Utilities
│       └── logging.py
├── app/                   # FastAPI dashboard
│   ├── main.py
│   └── templates/
│       └── dashboard.html
├── tests/                 # Test suite
├── scripts/               # Automation scripts
├── reports/               # Generated reports
├── .github/workflows/     # CI/CD
├── Dockerfile             # Docker config
├── fly.toml              # Fly.io config
└── pyproject.toml        # Python dependencies
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=portfolio --cov-report=html

# Specific test file
pytest tests/test_strategies.py -v

# Type checking
mypy portfolio/

# Linting
ruff check portfolio/ app/
```

## Strategy Details

### Momentum Sleeve
- **Universe**: S&P 500 top holdings
- **Signal**: Weighted momentum (3/6/12 month) + volume acceleration + sentiment
- **Weighting**: Inverse volatility with 20% max position
- **Rebalance**: Monthly

### Futuristic Sleeve
- **Universe**: Robotics (ROBO/BOTZ) + AI infrastructure + nuclear
- **Signal**: 6/12 month momentum × theme weight (robotics highest)
- **Weighting**: Equal weight
- **Rebalance**: Quarterly

### Real-World Sleeve
- **Universe**: XLI + XLP + XLE + XLU components
- **Signal**: Low beta + price stability + momentum
- **Weighting**: Equal weight
- **Rebalance**: Semi-annually

### Risk/Hedge Sleeve
- **Universe**: ETFs (SPY, IEF, TLT, XLV, XLU, VNQ, IWD, GLD, TIP, LQD)
- **Optimization**: Maximize Sharpe ratio
- **Constraints**: Long-only, beta ≤ 1.1, max weight 35%
- **Rebalance**: Weekly

## Risk Analytics

Computed metrics:
- **Beta (vs SPY)**: Portfolio sensitivity to market
- **Annualized Volatility**: Price fluctuation measure
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Largest peak-to-trough decline
- **Average Correlation**: Diversification measure

## Assumptions & Limitations

### Assumptions
- No transaction costs in paper mode
- Alpaca paper trading for MVP (real broker integration ready)
- Sentiment APIs stubbed to 0 if not configured (easily extensible)
- Static universes (can be made dynamic with screeners)
- Prices cached in Postgres to reduce API calls

### Limitations
- Long-only (no shorting or options)
- Single account (no multi-account support yet)
- No tax optimization
- No dividends/corporate actions handling
- Risk metrics use historical data (backward-looking)

### Future Enhancements
- Real sentiment integration (NewsAPI, Reddit PRAW)
- Dynamic universe generation (fundamental screeners)
- Multi-factor models (Fama-French)
- Tax-loss harvesting
- Multi-account support
- Backtesting engine
- Performance attribution

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

# Check migrations
python -c "from portfolio.db.repo import repo; print(repo.list_runs())"
```

### Price Data Issues

```bash
# Test price fetching
python -c "
from portfolio.data.prices import price_fetcher
from datetime import date, timedelta
end = date.today()
start = end - timedelta(days=30)
prices = price_fetcher.fetch_prices(['AAPL'], start, end, use_cache=False)
print(f'Fetched {len(prices.get(\"AAPL\", []))} prices for AAPL')
"
```

### Dashboard Not Loading

```bash
# Check if DB is accessible
python -c "from portfolio.db.repo import repo; print(repo.get_latest_run())"

# Check logs
uvicorn app.main:app --log-level debug
```

## API Documentation

When dashboard is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

- `GET /` - Dashboard HTML
- `GET /health` - Health check
- `GET /runs` - List runs (JSON)
- `GET /runs/{run_id}` - Run details (JSON)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run tests: `pytest`
5. Submit pull request

## License

MIT License - see LICENSE file

## Support

For issues or questions:
- Open a GitHub issue
- Check logs in `logs/` directory
- Review reports in `reports/` directory

## Acknowledgments

Built with:
- FastAPI
- Pandas/NumPy/SciPy
- yfinance
- Supabase/Postgres
- Alpaca API
- CVXPY (optional)
