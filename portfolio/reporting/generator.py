"""Report generation (markdown and CSV)."""

import csv
from datetime import date
from pathlib import Path

from portfolio.db.models import Allocation, Position, RiskAnalytics, Run, TradeOrder
from portfolio.utils.logging import logger


class ReportGenerator:
    """Generate markdown and CSV reports."""

    def __init__(self, output_dir: Path = Path("reports")):
        """Initialize report generator."""
        self.output_dir = output_dir

    def generate_report(
        self,
        run: Run,
        positions: list[Position],
        allocations: list[Allocation],
        orders: list[TradeOrder],
        risk_metrics: RiskAnalytics,
        notes: list[str] = None,
    ) -> tuple[Path, Path]:
        """
        Generate comprehensive report.

        Args:
            run: Run metadata
            positions: Current positions
            allocations: Target allocations
            orders: Trade orders
            risk_metrics: Risk analytics
            notes: Optional notes/warnings

        Returns:
            (markdown_path, csv_path)
        """
        # Create output directory
        run_dir = self.output_dir / str(run.asof_date)
        run_dir.mkdir(parents=True, exist_ok=True)

        # Generate markdown report
        md_path = run_dir / "report.md"
        self._generate_markdown(md_path, run, positions, allocations, orders, risk_metrics, notes)

        # Generate CSV of orders
        csv_path = run_dir / "orders.csv"
        self._generate_orders_csv(csv_path, orders)

        logger.info(f"Reports generated: {md_path}, {csv_path}")

        return md_path, csv_path

    def _generate_markdown(
        self,
        output_path: Path,
        run: Run,
        positions: list[Position],
        allocations: list[Allocation],
        orders: list[TradeOrder],
        risk_metrics: RiskAnalytics,
        notes: list[str] = None,
    ) -> None:
        """Generate markdown report."""
        lines = []

        # Header
        lines.append(f"# Portfolio Report: {run.asof_date}")
        lines.append("")
        lines.append(f"**Run ID:** {run.id}")
        lines.append(f"**Mode:** {run.mode.value}")
        lines.append(f"**Generated:** {run.created_at.strftime('%Y-%m-%d %H:%M:%S') if run.created_at else 'N/A'}")
        lines.append("")

        # NAV Summary
        lines.append("## Portfolio Summary")
        lines.append("")
        lines.append(f"- **Total NAV:** ${run.nav_total:,.2f}")
        lines.append(f"- **Cash Reserve:** ${run.nav_cash:,.2f}")
        lines.append(f"- **Momentum Sleeve:** ${run.nav_momentum:,.2f}")
        lines.append(f"- **Futuristic Sleeve:** ${run.nav_futuristic:,.2f}")
        lines.append(f"- **Real-World Sleeve:** ${run.nav_realworld:,.2f}")
        lines.append(f"- **Risk/Hedge Sleeve:** ${run.nav_risk:,.2f}")
        lines.append("")

        # Risk Metrics
        lines.append("## Risk Metrics")
        lines.append("")
        lines.append(f"- **Beta (vs SPY):** {risk_metrics.beta_spy:.3f}")
        lines.append(f"- **Annualized Volatility:** {risk_metrics.volatility_annual:.2%}")
        lines.append(f"- **Sharpe Ratio:** {risk_metrics.sharpe_ratio:.3f}")
        lines.append(f"- **Max Drawdown:** {risk_metrics.max_drawdown:.2%}")
        lines.append(f"- **Avg Correlation:** {risk_metrics.correlation_avg:.3f}")
        lines.append("")

        # Current Holdings
        lines.append("## Current Holdings")
        lines.append("")
        if positions:
            lines.append("| Sleeve | Ticker | Shares | Avg Cost | Market Price | Market Value |")
            lines.append("|--------|--------|--------|----------|--------------|--------------|")
            for pos in sorted(positions, key=lambda p: (p.sleeve.value, p.ticker)):
                lines.append(
                    f"| {pos.sleeve.value} | {pos.ticker} | {pos.shares:.2f} | "
                    f"${pos.avg_cost:.2f} | ${pos.market_price:.2f} | ${pos.market_value:,.2f} |"
                )
        else:
            lines.append("_No current holdings_")
        lines.append("")

        # Target Allocations
        lines.append("## Target Allocations")
        lines.append("")
        if allocations:
            lines.append("| Sleeve | Ticker | Target Weight | Target Dollars |")
            lines.append("|--------|--------|---------------|----------------|")
            for alloc in sorted(allocations, key=lambda a: (a.sleeve.value, -a.target_weight)):
                lines.append(
                    f"| {alloc.sleeve.value} | {alloc.ticker} | "
                    f"{alloc.target_weight:.2%} | ${alloc.target_dollars:,.2f} |"
                )
        else:
            lines.append("_No target allocations_")
        lines.append("")

        # Proposed Trades
        lines.append("## Proposed Trades")
        lines.append("")
        if orders:
            lines.append(f"**Total Orders:** {len(orders)}")
            lines.append("")
            lines.append("| Sleeve | Ticker | Side | Quantity | Notional | Limit Price | Reason |")
            lines.append("|--------|--------|------|----------|----------|-------------|--------|")
            for order in orders:
                lines.append(
                    f"| {order.sleeve.value} | {order.ticker} | {order.side.value.upper()} | "
                    f"{order.qty:.2f} | ${order.notional:,.2f} | "
                    f"${order.limit_price:.2f} | {order.reason} |"
                )
        else:
            lines.append("_No trades proposed_")
        lines.append("")

        # Notes
        if notes:
            lines.append("## Notes")
            lines.append("")
            for note in notes:
                lines.append(f"- {note}")
            lines.append("")

        # Write file
        output_path.write_text("\n".join(lines))

    def _generate_orders_csv(self, output_path: Path, orders: list[TradeOrder]) -> None:
        """Generate CSV of orders."""
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["sleeve", "ticker", "side", "quantity", "notional", "limit_price", "reason"]
            )

            for order in orders:
                writer.writerow([
                    order.sleeve.value,
                    order.ticker,
                    order.side.value,
                    f"{order.qty:.4f}",
                    f"{order.notional:.2f}",
                    f"{order.limit_price:.2f}" if order.limit_price else "",
                    order.reason,
                ])


# Global instance
report_generator = ReportGenerator()
