"""Live dashboard showing current Alpaca positions - no database required."""

from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from alpaca.trading.client import TradingClient
from portfolio.config import settings
from portfolio.utils.logging import logger

app = FastAPI(title="Portfolio Dashboard", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")

# Sleeve definitions
MOMENTUM = ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'META', 'AMZN', 'AMD', 'NFLX']
FUTURISTIC = ['PLTR', 'OKLO', 'SMR', 'AVGO', 'ARM', 'UEC', 'CCJ', 'UUUU', 'MU']
REALWORLD = ['JNJ', 'PG', 'KO', 'PEP', 'WMT', 'UNP', 'DUK', 'SO', 'EXC', 'AEP']
RISK = ['SPY', 'TLT', 'GLD', 'SHY']

@app.get("/health")
async def health():
    """Health check for Fly.io."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Live dashboard from Alpaca account."""
    try:
        # Connect to Alpaca
        trading_client = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=settings.alpaca_paper
        )

        # Get account and positions
        account = trading_client.get_account()
        positions = trading_client.get_all_positions()

        # Group positions by sleeve
        positions_by_sleeve = {
            'momentum': [],
            'futuristic': [],
            'realworld': [],
            'risk': []
        }

        for pos in positions:
            ticker = pos.symbol
            pos_data = {
                'ticker': ticker,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc) * 100,
            }

            if ticker in MOMENTUM:
                positions_by_sleeve['momentum'].append(pos_data)
            elif ticker in FUTURISTIC:
                positions_by_sleeve['futuristic'].append(pos_data)
            elif ticker in REALWORLD:
                positions_by_sleeve['realworld'].append(pos_data)
            elif ticker in RISK:
                positions_by_sleeve['risk'].append(pos_data)

        # Calculate sleeve totals
        sleeve_totals = {}
        for sleeve, sleeve_positions in positions_by_sleeve.items():
            total = sum(p['market_value'] for p in sleeve_positions)
            sleeve_totals[sleeve] = total

        # Portfolio summary
        portfolio_summary = {
            'cash': float(account.cash),
            'positions_value': float(account.long_market_value),
            'total_equity': float(account.equity),
            'buying_power': float(account.buying_power),
            'total_positions': len(positions),
        }

        # Calculate metrics
        equity = portfolio_summary['total_equity']
        metrics = {
            'cash_ratio': (portfolio_summary['cash'] / equity * 100) if equity > 0 else 0,
            'positions_ratio': (portfolio_summary['positions_value'] / equity * 100) if equity > 0 else 0,
            'using_margin': portfolio_summary['cash'] < 0,
        }

        # Load ticker descriptions
        try:
            from portfolio.data.ticker_descriptions import TICKER_DESCRIPTIONS
            ticker_descriptions = TICKER_DESCRIPTIONS
        except ImportError:
            ticker_descriptions = {}

        return templates.TemplateResponse(
            "live_dashboard.html",
            {
                "request": request,
                "portfolio": portfolio_summary,
                "positions_by_sleeve": positions_by_sleeve,
                "sleeve_totals": sleeve_totals,
                "metrics": metrics,
                "ticker_descriptions": ticker_descriptions,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e),
            },
        )
