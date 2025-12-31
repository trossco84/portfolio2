-- Initial schema for portfolio management system
-- Migration: 001_initial_schema

-- Runs table: tracks each portfolio run
CREATE TABLE IF NOT EXISTS runs (
    id SERIAL PRIMARY KEY,
    asof_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    nav_total NUMERIC(12, 2) NOT NULL,
    nav_momentum NUMERIC(12, 2),
    nav_futuristic NUMERIC(12, 2),
    nav_realworld NUMERIC(12, 2),
    nav_risk NUMERIC(12, 2),
    nav_cash NUMERIC(12, 2),
    mode VARCHAR(20) NOT NULL DEFAULT 'paper',
    notes TEXT,
    CONSTRAINT unique_asof_date UNIQUE (asof_date)
);

CREATE INDEX idx_runs_asof_date ON runs(asof_date DESC);
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);

-- Prices table: cached historical price data
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    adj_close NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4),
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    volume BIGINT,
    source VARCHAR(50) DEFAULT 'yfinance',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_ticker_date UNIQUE (ticker, date)
);

CREATE INDEX idx_prices_ticker_date ON prices(ticker, date DESC);
CREATE INDEX idx_prices_date ON prices(date DESC);

-- Signals table: computed signals for each run
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sleeve VARCHAR(20) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    signal_name VARCHAR(50) NOT NULL,
    value NUMERIC(12, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_signals_run_id ON signals(run_id);
CREATE INDEX idx_signals_sleeve_ticker ON signals(sleeve, ticker);

-- Allocations table: target allocations per run
CREATE TABLE IF NOT EXISTS allocations (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sleeve VARCHAR(20) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    target_weight NUMERIC(8, 6) NOT NULL,
    target_dollars NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_run_sleeve_ticker UNIQUE (run_id, sleeve, ticker)
);

CREATE INDEX idx_allocations_run_id ON allocations(run_id);
CREATE INDEX idx_allocations_sleeve ON allocations(sleeve);

-- Positions table: current holdings per run
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sleeve VARCHAR(20) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    shares NUMERIC(12, 4) NOT NULL,
    avg_cost NUMERIC(12, 4),
    market_price NUMERIC(12, 4) NOT NULL,
    market_value NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_run_sleeve_ticker_pos UNIQUE (run_id, sleeve, ticker)
);

CREATE INDEX idx_positions_run_id ON positions(run_id);
CREATE INDEX idx_positions_sleeve ON positions(sleeve);

-- Orders table: generated trade orders
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sleeve VARCHAR(20) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    qty NUMERIC(12, 4) NOT NULL,
    notional NUMERIC(12, 2) NOT NULL,
    limit_price NUMERIC(12, 4),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'filled', 'cancelled', 'rejected')),
    broker_order_id VARCHAR(100),
    filled_qty NUMERIC(12, 4),
    filled_avg_price NUMERIC(12, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_orders_run_id ON orders(run_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_sleeve ON orders(sleeve);

-- Risk metrics table: portfolio-level risk analytics
CREATE TABLE IF NOT EXISTS risk_metrics (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL,
    metric_value NUMERIC(12, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_risk_metrics_run_id ON risk_metrics(run_id);

-- Correlation matrix table: stores pairwise correlations
CREATE TABLE IF NOT EXISTS correlations (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ticker1 VARCHAR(20) NOT NULL,
    ticker2 VARCHAR(20) NOT NULL,
    correlation NUMERIC(8, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_correlations_run_id ON correlations(run_id);

COMMENT ON TABLE runs IS 'Portfolio run metadata and NAV snapshots';
COMMENT ON TABLE prices IS 'Cached historical price data';
COMMENT ON TABLE signals IS 'Computed strategy signals';
COMMENT ON TABLE allocations IS 'Target portfolio allocations';
COMMENT ON TABLE positions IS 'Current holdings snapshot';
COMMENT ON TABLE orders IS 'Generated trade orders';
COMMENT ON TABLE risk_metrics IS 'Portfolio risk analytics';
COMMENT ON TABLE correlations IS 'Asset correlation matrix';
