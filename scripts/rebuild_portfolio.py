#!/usr/bin/env python3
"""Rebuild portfolio from scratch with $8K invested ($2K per sleeve)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from portfolio.config import settings

# Portfolio configuration
SLEEVE_CAPITAL = 2000  # $2K per sleeve
MIN_POSITION = 100     # Minimum $100 per position

# Simplified universes
MOMENTUM = ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'META', 'AMZN', 'AMD', 'NFLX']
FUTURISTIC = ['PLTR', 'OKLO', 'SMR', 'AVGO', 'ARM', 'UEC', 'CCJ', 'UUUU', 'MU']
REALWORLD = ['JNJ', 'PG', 'KO', 'PEP', 'WMT', 'UNP', 'DUK', 'SO', 'EXC', 'AEP']
RISK = ['SPY', 'TLT', 'GLD', 'SHY']

def get_price(ticker):
    """Get current price for ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='1d')
        if len(hist) > 0:
            return float(hist['Close'].iloc[-1])
    except:
        pass
    return None

def get_valid_tickers(universe, n=8):
    """Select first N valid tickers with prices."""
    valid = []
    for ticker in universe:
        price = get_price(ticker)
        if price and price > 0:
            valid.append(ticker)
            if len(valid) >= n:
                break
    return valid

def main():
    print("="*90)
    print("REBUILD PORTFOLIO - $8K INVESTED ACROSS 4 SLEEVES")
    print("="*90)
    print()

    client = TradingClient(settings.alpaca_api_key, settings.alpaca_secret_key, paper=settings.alpaca_paper)
    
    account = client.get_account()
    cash = float(account.cash)
    print(f"Starting Cash: ${cash:,.2f}")
    
    if cash < 8000:
        print(f"ERROR: Need at least $8,000 cash. Current: ${cash:,.2f}")
        return
    
    print()
    print("Selecting positions for each sleeve...")
    print("-"*90)
    
    # Build allocation
    allocations = []
    
    print("\n[MOMENTUM SLEEVE - $2,000]")
    momentum_picks = get_valid_tickers(MOMENTUM, 8)
    if momentum_picks:
        capital_per = SLEEVE_CAPITAL / len(momentum_picks)
        for ticker in momentum_picks:
            allocations.append(('momentum', ticker, capital_per))
            print(f"  {ticker}: ${capital_per:.2f}")
    
    print("\n[FUTURISTIC SLEEVE - $2,000]")
    futuristic_picks = get_valid_tickers(FUTURISTIC, 8)
    if futuristic_picks:
        capital_per = SLEEVE_CAPITAL / len(futuristic_picks)
        for ticker in futuristic_picks:
            allocations.append(('futuristic', ticker, capital_per))
            print(f"  {ticker}: ${capital_per:.2f}")
    
    print("\n[REALWORLD SLEEVE - $2,000]")
    realworld_picks = get_valid_tickers(REALWORLD, 8)
    if realworld_picks:
        capital_per = SLEEVE_CAPITAL / len(realworld_picks)
        for ticker in realworld_picks:
            allocations.append(('realworld', ticker, capital_per))
            print(f"  {ticker}: ${capital_per:.2f}")
    
    print("\n[RISK SLEEVE - $2,000]")
    risk_picks = get_valid_tickers(RISK, 4)
    if risk_picks:
        capital_per = SLEEVE_CAPITAL / len(risk_picks)
        for ticker in risk_picks:
            allocations.append(('risk', ticker, capital_per))
            print(f"  {ticker}: ${capital_per:.2f}")
    
    print()
    print(f"Total allocations: {len(allocations)}")
    total_allocated = sum(a[2] for a in allocations)
    print(f"Total capital: ${total_allocated:,.2f}")
    print()
    
    # Build orders
    orders = []
    print("Computing orders...")
    print("-"*90)
    
    for sleeve, ticker, target_dollars in allocations:
        price = get_price(ticker)
        if not price:
            print(f"  ⚠️  No price for {ticker}, skipping")
            continue
        
        shares = int(target_dollars / price)
        
        if shares > 0 and shares * price >= MIN_POSITION:
            orders.append({
                'sleeve': sleeve,
                'ticker': ticker,
                'shares': shares,
                'price': price,
                'value': shares * price
            })
            print(f"  {ticker:<6} ({sleeve:<12}): {shares:>4} shares @ ${price:>8,.2f} = ${shares * price:>10,.2f}")
    
    total_cost = sum(o['value'] for o in orders)
    print()
    print(f"Total orders: {len(orders)}")
    print(f"Total cost: ${total_cost:,.2f}")
    print(f"Remaining cash: ${cash - total_cost:,.2f}")
    print()
    
    # Confirm
    response = input("Execute these orders? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Execute
    print()
    print("Executing orders...")
    print("-"*90)
    
    successful = 0
    failed = 0
    
    for order in orders:
        try:
            req = MarketOrderRequest(
                symbol=order['ticker'],
                qty=order['shares'],
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            resp = client.submit_order(req)
            print(f"  ✓ BUY {order['ticker']}: {order['shares']} shares - {resp.id}")
            successful += 1
        except Exception as e:
            print(f"  ✗ BUY {order['ticker']}: {e}")
            failed += 1
    
    print()
    print("="*90)
    print(f"COMPLETE: {successful} successful, {failed} failed")
    print("="*90)
    
    # Final status
    import time
    time.sleep(3)
    account = client.get_account()
    positions = client.get_all_positions()
    
    print()
    print(f"Final Cash: ${float(account.cash):,.2f}")
    print(f"Final Equity: ${float(account.equity):,.2f}")
    print(f"Final Positions: {len(positions)}")
    print()

if __name__ == '__main__':
    main()
