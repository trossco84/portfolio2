"""FastAPI dashboard for portfolio viewer."""

import secrets
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from portfolio.config import settings
from portfolio.db.repo import repo
from portfolio.utils.logging import logger

app = FastAPI(title="Portfolio Dashboard", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic auth middleware (if configured)."""
    if not settings.dashboard_username or not settings.dashboard_password:
        # No auth configured
        return True

    correct_username = secrets.compare_digest(
        credentials.username, settings.dashboard_username
    )
    correct_password = secrets.compare_digest(
        credentials.password, settings.dashboard_password
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return True


@app.get("/health")
async def health():
    """Health check for Fly.io."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, auth: bool = Depends(check_auth)):
    """Main dashboard view."""
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
            },
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "dashboard.html", {"request": request, "error": str(e)}
        )


@app.get("/runs")
async def list_runs(auth: bool = Depends(check_auth), limit: int = 50):
    """List recent runs."""
    try:
        runs = repo.list_runs(limit=limit)
        return {
            "runs": [
                {
                    "id": r.id,
                    "asof_date": r.asof_date.isoformat(),
                    "nav_total": float(r.nav_total),
                    "mode": r.mode.value,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in runs
            ]
        }
    except Exception as e:
        logger.error(f"Error listing runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{run_id}")
async def get_run(run_id: int, auth: bool = Depends(check_auth)):
    """Get run details."""
    try:
        run = repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        positions = repo.get_positions(run_id)
        allocations = repo.get_allocations(run_id)
        orders = repo.get_orders(run_id)
        risk_metrics = repo.get_risk_metrics(run_id)
        signals = repo.get_signals(run_id)

        return {
            "run": {
                "id": run.id,
                "asof_date": run.asof_date.isoformat(),
                "nav_total": float(run.nav_total),
                "nav_momentum": float(run.nav_momentum) if run.nav_momentum else None,
                "nav_futuristic": float(run.nav_futuristic) if run.nav_futuristic else None,
                "nav_realworld": float(run.nav_realworld) if run.nav_realworld else None,
                "nav_risk": float(run.nav_risk) if run.nav_risk else None,
                "nav_cash": float(run.nav_cash) if run.nav_cash else None,
                "mode": run.mode.value,
                "notes": run.notes,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            },
            "positions": [
                {
                    "sleeve": p.sleeve.value,
                    "ticker": p.ticker,
                    "shares": float(p.shares),
                    "market_price": float(p.market_price),
                    "market_value": float(p.market_value),
                }
                for p in positions
            ],
            "allocations": [
                {
                    "sleeve": a.sleeve.value,
                    "ticker": a.ticker,
                    "target_weight": float(a.target_weight),
                    "target_dollars": float(a.target_dollars),
                }
                for a in allocations
            ],
            "orders": [
                {
                    "sleeve": o.sleeve.value,
                    "ticker": o.ticker,
                    "side": o.side.value,
                    "qty": float(o.qty),
                    "notional": float(o.notional),
                    "status": o.status.value,
                }
                for o in orders
            ],
            "risk_metrics": {m.metric_name: float(m.metric_value) for m in risk_metrics},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
