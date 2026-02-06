"""Simple FastAPI dashboard for portfolio viewer - no authentication."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from portfolio.db.repo import repo
from portfolio.utils.logging import logger

app = FastAPI(title="Portfolio Dashboard", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page - no auth required."""
    try:
        # Get latest run
        latest_run = repo.get_latest_run()

        if not latest_run:
            return templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    "error": "No runs found. Please run the portfolio first.",
                },
            )

        # Get data for latest run
        positions = repo.get_positions(latest_run.id)
        allocations = repo.get_allocations(latest_run.id)
        orders = repo.get_orders(latest_run.id)
        risk_metrics = repo.get_risk_metrics(latest_run.id)

        # Format risk metrics
        risk_dict = {m.metric_name: float(m.metric_value) for m in risk_metrics}

        # Group positions by sleeve
        positions_by_sleeve = {}
        for pos in positions:
            sleeve = pos.sleeve.value
            if sleeve not in positions_by_sleeve:
                positions_by_sleeve[sleeve] = []
            positions_by_sleeve[sleeve].append(pos)

        # Group allocations by sleeve
        allocations_by_sleeve = {}
        for alloc in allocations:
            sleeve = alloc.sleeve.value
            if sleeve not in allocations_by_sleeve:
                allocations_by_sleeve[sleeve] = []
            allocations_by_sleeve[sleeve].append(alloc)

        # Load ticker descriptions
        try:
            from portfolio.data.ticker_descriptions import TICKER_DESCRIPTIONS
            ticker_descriptions = TICKER_DESCRIPTIONS
        except ImportError:
            ticker_descriptions = {}

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "run": latest_run,
                "positions": positions,
                "positions_by_sleeve": positions_by_sleeve,
                "allocations": allocations,
                "allocations_by_sleeve": allocations_by_sleeve,
                "orders": orders,
                "risk_metrics": risk_dict,
                "ticker_descriptions": ticker_descriptions,
            },
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "dashboard.html", {"request": request, "error": str(e)}
        )
