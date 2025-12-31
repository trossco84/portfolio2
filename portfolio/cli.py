"""CLI interface for portfolio management."""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal

from portfolio.config import settings
from portfolio.db.models import (
    Allocation,
    Correlation,
    Order,
    OrderStatus,
    Position,
    RiskMetric,
    Run,
    RunMode,
    Signal,
    Sleeve,
)
from portfolio.db.repo import repo
from portfolio.execution.alpaca_broker import alpaca_broker
from portfolio.execution.paper_broker import paper_broker
from portfolio.optimizer.trade_plan import trade_planner
from portfolio.reporting.generator import report_generator
from portfolio.risk.analytics import risk_analytics
from portfolio.strategies.futuristic.strategy import futuristic_strategy
from portfolio.strategies.momentum.strategy import momentum_strategy
from portfolio.strategies.realworld.strategy import realworld_strategy
from portfolio.strategies.risk.strategy import risk_strategy
from portfolio.utils.logging import logger


class PortfolioRunner:
    """Main portfolio run orchestrator."""

    def __init__(self):
        """Initialize portfolio runner."""
        self.repo = repo

    def run(self, asof_date: date, mode: str = "paper") -> int:
        """
        Execute full portfolio run.

        Args:
            asof_date: Date to run as of
            mode: 'paper' or 'live'

        Returns:
            Run ID
        """
        logger.info(f"Starting portfolio run for {asof_date} in {mode} mode")

        run_mode = RunMode.PAPER if mode == "paper" else RunMode.LIVE

        # Step 1: Generate signals for each sleeve
        logger.info("Generating strategy signals...")
        momentum_signals = momentum_strategy.generate_signals(asof_date)
        futuristic_signals = futuristic_strategy.generate_signals(asof_date)
        realworld_signals = realworld_strategy.generate_signals(asof_date)
        risk_signals = risk_strategy.generate_signals(asof_date)

        # Step 2: Compute target allocations
        logger.info("Computing target allocations...")
        sleeve_capital = settings.sleeve_capital

        momentum_weights = momentum_strategy.compute_target_weights(momentum_signals, sleeve_capital)
        futuristic_weights = futuristic_strategy.compute_target_weights(futuristic_signals, sleeve_capital)
        realworld_weights = realworld_strategy.compute_target_weights(realworld_signals, sleeve_capital)
        risk_weights = risk_strategy.compute_target_weights(risk_signals, sleeve_capital)

        # Build allocations
        allocations = []

        for ticker, weight in momentum_weights.items():
            allocations.append(
                Allocation(
                    run_id=0,  # Will be set after run creation
                    sleeve=Sleeve.MOMENTUM,
                    ticker=ticker,
                    target_weight=weight,
                    target_dollars=weight * sleeve_capital,
                )
            )

        for ticker, weight in futuristic_weights.items():
            allocations.append(
                Allocation(
                    run_id=0,
                    sleeve=Sleeve.FUTURISTIC,
                    ticker=ticker,
                    target_weight=weight,
                    target_dollars=weight * sleeve_capital,
                )
            )

        for ticker, weight in realworld_weights.items():
            allocations.append(
                Allocation(
                    run_id=0,
                    sleeve=Sleeve.REALWORLD,
                    ticker=ticker,
                    target_weight=weight,
                    target_dollars=weight * sleeve_capital,
                )
            )

        for ticker, weight in risk_weights.items():
            allocations.append(
                Allocation(
                    run_id=0,
                    sleeve=Sleeve.RISK,
                    ticker=ticker,
                    target_weight=weight,
                    target_dollars=weight * sleeve_capital,
                )
            )

        # Step 3: Compute portfolio risk metrics
        logger.info("Computing risk metrics...")
        risk_metrics = risk_analytics.compute_risk_metrics(allocations, asof_date)
        correlations = risk_analytics.compute_correlation_matrix(allocations, asof_date)

        # Step 4: Get current positions (from latest run)
        logger.info("Loading current positions...")
        latest_run = self.repo.get_latest_run()
        if latest_run and latest_run.asof_date < asof_date:
            current_positions = self.repo.get_positions(latest_run.id)
        else:
            current_positions = []

        # Step 5: Generate trade plan
        logger.info("Generating trade plan...")
        orders = trade_planner.generate_trade_plan(current_positions, allocations, asof_date)

        # Validate
        sleeve_caps = {
            Sleeve.MOMENTUM: sleeve_capital,
            Sleeve.FUTURISTIC: sleeve_capital,
            Sleeve.REALWORLD: sleeve_capital,
            Sleeve.RISK: sleeve_capital,
        }
        is_valid, warnings = trade_planner.validate_trade_plan(orders, sleeve_caps)

        if warnings:
            for warning in warnings:
                logger.warning(f"Trade plan validation: {warning}")

        # Step 6: Create run record
        logger.info("Saving run to database...")
        run = Run(
            asof_date=asof_date,
            nav_total=settings.total_capital,
            nav_cash=settings.cash_reserve,
            nav_momentum=sleeve_capital,
            nav_futuristic=sleeve_capital,
            nav_realworld=sleeve_capital,
            nav_risk=sleeve_capital,
            mode=run_mode,
            notes=f"Generated {len(orders)} orders, {len(allocations)} allocations",
        )

        run_id = self.repo.create_run(run)
        logger.info(f"Created run {run_id}")

        # Update allocations and signals with run_id
        for alloc in allocations:
            alloc.run_id = run_id
        self.repo.bulk_create_allocations(allocations)

        # Save signals
        all_signals = []
        for sig in momentum_signals:
            all_signals.append(
                Signal(
                    run_id=run_id,
                    sleeve=Sleeve.MOMENTUM,
                    ticker=sig.ticker,
                    signal_name="composite_score",
                    value=sig.score,
                )
            )
        for sig in futuristic_signals:
            all_signals.append(
                Signal(
                    run_id=run_id,
                    sleeve=Sleeve.FUTURISTIC,
                    ticker=sig.ticker,
                    signal_name="composite_score",
                    value=sig.score,
                )
            )
        for sig in realworld_signals:
            all_signals.append(
                Signal(
                    run_id=run_id,
                    sleeve=Sleeve.REALWORLD,
                    ticker=sig.ticker,
                    signal_name="composite_score",
                    value=sig.score,
                )
            )
        for sig in risk_signals:
            all_signals.append(
                Signal(
                    run_id=run_id,
                    sleeve=Sleeve.RISK,
                    ticker=sig.ticker,
                    signal_name="optimized_weight",
                    value=sig.score,
                )
            )

        self.repo.bulk_create_signals(all_signals)

        # Save risk metrics
        risk_metric_records = [
            RiskMetric(run_id=run_id, metric_name="beta_spy", metric_value=risk_metrics.beta_spy),
            RiskMetric(run_id=run_id, metric_name="volatility_annual", metric_value=risk_metrics.volatility_annual),
            RiskMetric(run_id=run_id, metric_name="sharpe_ratio", metric_value=risk_metrics.sharpe_ratio),
            RiskMetric(run_id=run_id, metric_name="max_drawdown", metric_value=risk_metrics.max_drawdown),
            RiskMetric(run_id=run_id, metric_name="correlation_avg", metric_value=risk_metrics.correlation_avg),
        ]
        self.repo.bulk_create_risk_metrics(risk_metric_records)

        # Save correlations
        corr_records = [
            Correlation(run_id=run_id, ticker1=t1, ticker2=t2, correlation=corr)
            for (t1, t2), corr in correlations.items()
        ]
        if corr_records:
            self.repo.bulk_create_correlations(corr_records)

        # Save positions (same as allocations for now, with computed shares)
        from portfolio.data.prices import price_fetcher

        position_records = []
        for alloc in allocations:
            price = price_fetcher.get_latest_price(alloc.ticker, asof_date)
            if price:
                shares = alloc.target_dollars / price
                position_records.append(
                    Position(
                        run_id=run_id,
                        sleeve=alloc.sleeve,
                        ticker=alloc.ticker,
                        shares=shares,
                        avg_cost=price,
                        market_price=price,
                        market_value=alloc.target_dollars,
                    )
                )

        if position_records:
            self.repo.bulk_create_positions(position_records)

        # Save orders
        order_records = []
        for trade_order in orders:
            order_records.append(
                Order(
                    run_id=run_id,
                    sleeve=trade_order.sleeve,
                    ticker=trade_order.ticker,
                    side=trade_order.side,
                    qty=trade_order.qty,
                    notional=trade_order.notional,
                    limit_price=trade_order.limit_price,
                    status=OrderStatus.PENDING,
                )
            )

        if order_records:
            self.repo.bulk_create_orders(order_records)

        # Step 7: Generate report
        logger.info("Generating reports...")
        run.id = run_id  # Set ID for report
        md_path, csv_path = report_generator.generate_report(
            run=run,
            positions=position_records,
            allocations=allocations,
            orders=orders,
            risk_metrics=risk_metrics,
            notes=warnings,
        )

        logger.info(f"Portfolio run complete: {run_id}")
        logger.info(f"Reports: {md_path}, {csv_path}")

        return run_id

    def report(self, asof_date: date) -> None:
        """Generate report for an existing run."""
        logger.info(f"Generating report for {asof_date}")

        run = self.repo.get_run_by_date(asof_date)
        if not run:
            logger.error(f"No run found for {asof_date}")
            return

        positions = self.repo.get_positions(run.id)
        allocations = self.repo.get_allocations(run.id)
        db_orders = self.repo.get_orders(run.id)

        # Convert Order to TradeOrder for report
        from portfolio.db.models import TradeOrder

        trade_orders = [
            TradeOrder(
                sleeve=o.sleeve,
                ticker=o.ticker,
                side=o.side,
                qty=o.qty,
                notional=o.notional,
                limit_price=o.limit_price,
                reason=f"Status: {o.status.value}",
            )
            for o in db_orders
        ]

        # Get risk metrics
        risk_metric_records = self.repo.get_risk_metrics(run.id)
        risk_metrics_dict = {m.metric_name: m.metric_value for m in risk_metric_records}

        from portfolio.db.models import RiskAnalytics

        risk_metrics = RiskAnalytics(
            beta_spy=risk_metrics_dict.get("beta_spy", Decimal("1.0")),
            volatility_annual=risk_metrics_dict.get("volatility_annual", Decimal("0.15")),
            sharpe_ratio=risk_metrics_dict.get("sharpe_ratio", Decimal("0.0")),
            max_drawdown=risk_metrics_dict.get("max_drawdown", Decimal("0.0")),
            correlation_avg=risk_metrics_dict.get("correlation_avg", Decimal("0.5")),
        )

        md_path, csv_path = report_generator.generate_report(
            run=run,
            positions=positions,
            allocations=allocations,
            orders=trade_orders,
            risk_metrics=risk_metrics,
        )

        logger.info(f"Report generated: {md_path}, {csv_path}")


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Multi-strategy portfolio manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run portfolio optimization")
    run_parser.add_argument(
        "--asof", type=str, required=True, help="As-of date (YYYY-MM-DD)"
    )
    run_parser.add_argument(
        "--mode", type=str, default="paper", choices=["paper", "live"], help="Execution mode"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report for existing run")
    report_parser.add_argument(
        "--asof", type=str, required=True, help="As-of date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    runner = PortfolioRunner()

    try:
        if args.command == "run":
            asof_date = datetime.strptime(args.asof, "%Y-%m-%d").date()
            run_id = runner.run(asof_date, args.mode)
            print(f"\nPortfolio run completed successfully: Run ID {run_id}")
            print(f"Check reports/{asof_date}/ for outputs")

        elif args.command == "report":
            asof_date = datetime.strptime(args.asof, "%Y-%m-%d").date()
            runner.report(asof_date)
            print(f"\nReport generated for {asof_date}")

    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
