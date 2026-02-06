#!/usr/bin/env python3
"""
Full portfolio rebalance with fresh data fetch and LLM analysis.
Runs independently without database dependency.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from portfolio.data.prices import price_provider
from portfolio.strategies.momentum.strategy import MomentumStrategy
from portfolio.strategies.futuristic.strategy import FuturisticStrategy
from portfolio.strategies.realworld.strategy import RealWorldStrategy
from portfolio.strategies.risk.strategy import RiskStrategy
from portfolio.risk.analytics import risk_analytics
from portfolio.ai.analysis import portfolio_analyzer
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


def main():
    today = date.today()

    print("=" * 100)
    print(f"FULL PORTFOLIO REBALANCE - {today}")
    print("=" * 100)
    print()

    # Connect to Alpaca
    trading_client = TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper
    )

    # Get account info
    account = trading_client.get_account()
    cash = float(account.cash)
    equity = float(account.equity)
    positions_value = float(account.long_market_value)

    print("CURRENT ACCOUNT")
    print("-" * 100)
    print(f"Cash:             ${cash:>12,.2f}")
    print(f"Positions Value:  ${positions_value:>12,.2f}")
    print(f"Total Equity:     ${equity:>12,.2f}")
    print(f"Using Margin:     {cash < 0}")
    print()

    # Configuration
    total_capital = Decimal(str(settings.total_capital))
    cash_reserve = Decimal(str(settings.cash_reserve))
    sleeve_capital = Decimal(str(settings.sleeve_capital))

    print("CAPITAL ALLOCATION")
    print("-" * 100)
    print(f"Total Capital:    ${float(total_capital):>12,.2f}")
    print(f"Cash Reserve:     ${float(cash_reserve):>12,.2f}")
    print(f"Per Sleeve:       ${float(sleeve_capital):>12,.2f}")
    print(f"Total Invested:   ${float(sleeve_capital * 4):>12,.2f}")
    print()

    # Initialize strategies
    momentum_strategy = MomentumStrategy()
    futuristic_strategy = FuturisticStrategy()
    realworld_strategy = RealWorldStrategy()
    risk_strategy = RiskStrategy()

    # Generate signals for each sleeve
    print("GENERATING SIGNALS (this may take a few minutes...)")
    print("-" * 100)

    print("Fetching momentum signals...")
    momentum_signals = momentum_strategy.generate_signals(today)
    print(f"  ✓ Generated {len(momentum_signals)} momentum signals")

    print("Fetching futuristic signals...")
    futuristic_signals = futuristic_strategy.generate_signals(today)
    print(f"  ✓ Generated {len(futuristic_signals)} futuristic signals")

    print("Fetching realworld signals...")
    realworld_signals = realworld_strategy.generate_signals(today)
    print(f"  ✓ Generated {len(realworld_signals)} realworld signals")

    print("Fetching risk signals...")
    risk_signals = risk_strategy.generate_signals(today)
    print(f"  ✓ Generated {len(risk_signals)} risk signals")
    print()

    # Compute target allocations
    print("COMPUTING TARGET ALLOCATIONS")
    print("-" * 100)

    momentum_allocs = momentum_strategy.compute_target_weights(momentum_signals, sleeve_capital)
    print(f"Momentum sleeve:   {len(momentum_allocs)} positions")

    futuristic_allocs = futuristic_strategy.compute_target_weights(futuristic_signals, sleeve_capital)
    print(f"Futuristic sleeve: {len(futuristic_allocs)} positions")

    realworld_allocs = realworld_strategy.compute_target_weights(realworld_signals, sleeve_capital)
    print(f"Real-world sleeve: {len(realworld_allocs)} positions")

    risk_allocs = risk_strategy.compute_target_weights(risk_signals, sleeve_capital)
    print(f"Risk sleeve:       {len(risk_allocs)} positions")
    print()

    # Combine all allocations
    all_allocations = momentum_allocs + futuristic_allocs + realworld_allocs + risk_allocs

    # Get current positions from Alpaca
    current_positions = {}
    alpaca_positions = trading_client.get_all_positions()
    for pos in alpaca_positions:
        current_positions[pos.symbol] = {
            'qty': float(pos.qty),
            'market_value': float(pos.market_value),
            'current_price': float(pos.current_price)
        }

    print(f"Current positions: {len(current_positions)}")
    print()

    # Compute trades needed
    print("COMPUTING TRADE PLAN")
    print("-" * 100)

    trades = []
    target_tickers = set()

    for alloc in all_allocations:
        ticker = alloc.ticker
        target_tickers.add(ticker)
        target_dollars = float(alloc.target_dollars)

        # Get current price
        prices = price_provider.get_latest_prices([ticker])
        if ticker not in prices:
            print(f"  ⚠️  No price for {ticker}, skipping")
            continue

        current_price = float(prices[ticker])
        target_shares = int(target_dollars / current_price)

        current_shares = int(current_positions.get(ticker, {}).get('qty', 0))
        shares_diff = target_shares - current_shares

        if abs(shares_diff) > 0 and abs(shares_diff * current_price) >= settings.min_trade_size:
            trades.append({
                'ticker': ticker,
                'side': 'BUY' if shares_diff > 0 else 'SELL',
                'shares': abs(shares_diff),
                'price': current_price,
                'value': abs(shares_diff) * current_price,
                'sleeve': alloc.sleeve.value,
                'current_shares': current_shares,
                'target_shares': target_shares
            })

    # Find positions to close (not in target)
    for ticker, pos_info in current_positions.items():
        if ticker not in target_tickers:
            trades.append({
                'ticker': ticker,
                'side': 'SELL',
                'shares': int(pos_info['qty']),
                'price': pos_info['current_price'],
                'value': pos_info['market_value'],
                'sleeve': 'CLOSE',
                'current_shares': int(pos_info['qty']),
                'target_shares': 0
            })

    # Sort trades: sells first, then buys
    trades.sort(key=lambda t: (t['side'] == 'BUY', -t['value']))

    total_buy = sum(t['value'] for t in trades if t['side'] == 'BUY')
    total_sell = sum(t['value'] for t in trades if t['side'] == 'SELL')

    print(f"Trades needed: {len(trades)}")
    print(f"  SELL: {sum(1 for t in trades if t['side'] == 'SELL')} orders, ${total_sell:,.2f}")
    print(f"  BUY:  {sum(1 for t in trades if t['side'] == 'BUY')} orders, ${total_buy:,.2f}")
    print(f"Net:    ${total_buy - total_sell:,.2f}")
    print()

    # Show detailed trade plan
    print("DETAILED TRADE PLAN")
    print("-" * 100)
    print(f"{'Side':<6} {'Ticker':<8} {'Shares':>8} {'Price':>10} {'Value':>12} {'Sleeve':<12} {'Current→Target'}")
    print("-" * 100)

    for trade in trades:
        print(f"{trade['side']:<6} {trade['ticker']:<8} {trade['shares']:>8} ${trade['price']:>9,.2f} ${trade['value']:>11,.2f} {trade['sleeve']:<12} {trade['current_shares']}→{trade['target_shares']}")
    print()

    # Generate AI analysis if available
    if settings.anthropic_api_key:
        print("GENERATING AI ANALYSIS")
        print("-" * 100)

        # Build portfolio summary for AI
        portfolio_data = {
            'nav_total': equity,
            'cash': cash,
            'positions_value': positions_value
        }

        positions_summary = [
            {
                'ticker': ticker,
                'shares': pos['qty'],
                'market_value': pos['market_value'],
                'current_price': pos['current_price']
            }
            for ticker, pos in current_positions.items()
        ]

        # Compute simple metrics
        metrics = {
            'cash_ratio': cash / equity if equity > 0 else 0,
            'position_count': len(current_positions)
        }

        ai_analysis = portfolio_analyzer.analyze_portfolio(
            portfolio_data=portfolio_data,
            positions=positions_summary,
            metrics=metrics,
            recommended_trades=trades
        )

        print(ai_analysis)
        print()

    # Confirm execution
    print("=" * 100)
    response = input("Execute these trades? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return

    # Execute trades
    print()
    print("EXECUTING TRADES")
    print("-" * 100)

    successful = 0
    failed = 0

    for trade in trades:
        ticker = trade['ticker']
        side = OrderSide.BUY if trade['side'] == 'BUY' else OrderSide.SELL
        shares = trade['shares']

        try:
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY
            )

            response = trading_client.submit_order(order_request)
            print(f"  ✓ {trade['side']} {ticker}: {shares} shares - Order {response.id}")
            successful += 1

        except Exception as e:
            print(f"  ✗ {trade['side']} {ticker}: {shares} shares - FAILED: {e}")
            failed += 1

    print()
    print("=" * 100)
    print(f"EXECUTION COMPLETE: {successful} successful, {failed} failed")
    print("=" * 100)

    # Show final account status
    print()
    print("Fetching updated account status...")
    import time
    time.sleep(3)  # Wait for orders to process

    account = trading_client.get_account()
    print()
    print("FINAL ACCOUNT STATUS")
    print("-" * 100)
    print(f"Cash:             ${float(account.cash):>12,.2f}")
    print(f"Positions Value:  ${float(account.long_market_value):>12,.2f}")
    print(f"Total Equity:     ${float(account.equity):>12,.2f}")
    print(f"Using Margin:     {float(account.cash) < 0}")
    print()


if __name__ == "__main__":
    main()
