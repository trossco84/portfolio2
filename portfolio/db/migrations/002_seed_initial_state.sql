-- Seed script: Initialize cash reserve state
-- Migration: 002_seed_initial_state

-- This creates an initial run representing the starting state
-- You can modify the asof_date to match your actual start date

INSERT INTO runs (asof_date, nav_total, nav_cash, nav_momentum, nav_futuristic, nav_realworld, nav_risk, mode, notes)
VALUES (
    '2025-01-01',
    25000.00,
    5000.00,
    5000.00,
    5000.00,
    5000.00,
    5000.00,
    'initial',
    'Initial portfolio state: $25K total, $5K cash reserve, $5K per sleeve'
)
ON CONFLICT (asof_date) DO NOTHING;

-- Add a cash position to track the reserve
INSERT INTO positions (run_id, sleeve, ticker, shares, avg_cost, market_price, market_value)
SELECT
    id,
    'cash',
    'USD',
    5000.00,
    1.00,
    1.00,
    5000.00
FROM runs
WHERE asof_date = '2025-01-01'
ON CONFLICT (run_id, sleeve, ticker) DO NOTHING;
