#!/usr/bin/env python3
"""Quick portfolio rebalance - direct approach without database."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from portfolio.config import settings
from decimal import Decimal

# Target allocation - adjust as needed
TARGET_CAPITAL = 10000  # $8K invested + $2K cash reserve
SLEEVE_CAPITAL = 2000   # $2K per sleeve

# Simple universes - top stocks by category
MOMENTUM_UNIVERSE = ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'AMZN']
FUTURISTIC_UNIVERSE = ['PLTR', 'OKLO', 'AMD', 'AVGO', 'TSM']
REALWORLD_UNIVERSE = ['JNJ', 'PG', 'KO', 'WMT', 'DUK']
RISK_UNIVERSE = ['SPY', 'TLT', 'GLD']

def get_momentum_scores(tickers):
    """Simple momentum: 6-month return."""
    scores = {}
    for ticker in tickers:
        try:
            data = yf.download(ticker, period='6mo', progress=False)
            if len(data) > 20:
                ret = (data['Adj Close'].iloc[-1] / data['Adj Close'].iloc[0] - 1) * 100
                scores[ticker] = float(ret)
        except:
            pass
    return scores

def main():
    print("="*80)
    print("QUICK PORTFOLIO REBALANCE")
    print("="*80)
    print()

    # Connect to Alpaca
    client = TradingClient(settings.alpaca_api_key, settings.alpaca_secret_key, paper=settings.alpaca_paper)
    
    # Get current state
    account = client.get_account()
    cash = float(account.cash)
    equity = float(account.equity)
    
    print(f"Current Cash: ${cash:,.2f}")
    print(f"Total Equity: ${equity:,.2f}")
    print(f"Using Margin: {cash < 0}")
    print()

    # Generate simple signals
    print("Generating signals...")
    momentum_scores = get_momentum_scores(MOMENTUM_UNIVERSE)
    futuristic_scores = get_momentum_scores(FUTURISTIC_UNIVERSE)
    realworld_scores = get_momentum_scores(REALWORLD_UNIVERSE)
    
    # Select top 3 from each sleeve
    momentum_picks = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    futuristic_picks = sorted(futuristic_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    realworld_picks = sorted(realworld_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    risk_picks = [('SPY', 100), ('TLT', 50)]  # Static risk allocation
    
    # Build target allocations
    targets = {}
    
    # Equal weight within each sleeve
    for ticker, score in momentum_picks:
        targets[ticker] = SLEEVE_CAPITAL / 3
    for ticker, score in futuristic_picks:
        targets[ticker] = SLEEVE_CAPITAL / 3
    for ticker, score in realworld_picks:
        targets[ticker] = SLEEVE_CAPITAL / 3
    for ticker, weight in risk_picks:
        targets[ticker] = SLEEVE_CAPITAL * weight / 100
    
    print(f"\nTarget portfolio: {len(targets)} positions")
    for ticker, target_dollars in sorted(targets.items()):
        print(f"  {ticker}: ${target_dollars:.2f}")
    print()

    # Get current positions
    current_positions = {}
    try:
        positions = client.get_all_positions()
        for pos in positions:
            current_positions[pos.symbol] = {
                'qty': float(pos.qty),
                'price': float(pos.current_price),
                'value': float(pos.market_value)
            }
    except:
        pass
    
    print(f"Current positions: {len(current_positions)}")
    
    # Calculate trades
    trades = []
    
    # Buys/adjusts for target positions
    for ticker, target_dollars in targets.items():
        try:
            current_value = current_positions.get(ticker, {}).get('value', 0)
            diff = target_dollars - current_value
            
            if abs(diff) > 50:  # Min $50 trade
                # Get current price
                data = yf.download(ticker, period='1d', progress=False)
                if len(data) > 0:
                    price = float(data['Adj Close'].iloc[-1])
                    target_shares = int(target_dollars / price)
                    current_shares = int(current_positions.get(ticker, {}).get('qty', 0))
                    shares_diff = target_shares - current_shares
                    
                    if shares_diff != 0:
                        trades.append({
                            'ticker': ticker,
                            'side': 'BUY' if shares_diff > 0 else 'SELL',
                            'shares': abs(shares_diff),
                            'price': price
                        })
        except Exception as e:
            print(f"  Error processing {ticker}: {e}")
    
    # Sells for positions not in target
    for ticker in current_positions:
        if ticker not in targets:
            trades.append({
                'ticker': ticker,
                'side': 'SELL',
                'shares': int(current_positions[ticker]['qty']),
                'price': current_positions[ticker]['price']
            })
    
    # Show trade plan
    print("\nTrade Plan:")
    print("-"*80)
    total_buy = sum(t['shares'] * t['price'] for t in trades if t['side'] == 'BUY')
    total_sell = sum(t['shares'] * t['price'] for t in trades if t['side'] == 'SELL')
    
    for trade in sorted(trades, key=lambda t: (t['side'] == 'BUY', -t['shares'] * t['price'])):
        value = trade['shares'] * trade['price']
        print(f"{trade['side']:<6} {trade['ticker']:<8} {trade['shares']:>6} shares @ ${trade['price']:>8,.2f} = ${value:>10,.2f}")
    
    print(f"\nTotal SELL: ${total_sell:,.2f}")
    print(f"Total BUY:  ${total_buy:,.2f}")
    print(f"Net:        ${total_buy - total_sell:,.2f}")
    print()
    
    # Confirm
    response = input("Execute trades? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Execute
    print("\nExecuting...")
    for trade in trades:
        try:
            order = MarketOrderRequest(
                symbol=trade['ticker'],
                qty=trade['shares'],
                side=OrderSide.BUY if trade['side'] == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            resp = client.submit_order(order)
            print(f"  ✓ {trade['side']} {trade['ticker']}: {trade['shares']} shares - {resp.id}")
        except Exception as e:
            print(f"  ✗ {trade['side']} {trade['ticker']}: {e}")
    
    print("\nDone!")

if __name__ == '__main__':
    main()
