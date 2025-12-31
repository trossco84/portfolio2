"""Static universes for each sleeve."""

# Momentum sleeve: Large cap US tech and growth stocks (simplified S&P top holdings)
MOMENTUM_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "V", "JNJ",
    "WMT", "JPM", "MA", "PG", "UNH", "HD", "DIS", "BAC", "ADBE", "CRM",
    "NFLX", "PFE", "KO", "PEP", "CSCO", "INTC", "AMD", "QCOM", "TXN", "ORCL",
]

# Futuristic sleeve: Robotics, AI infrastructure, and nuclear
# Based on components from ROBO/BOTZ ETFs + nuclear + AI infra
FUTURISTIC_UNIVERSE = [
    # Robotics & Automation
    "ISRG", "ABB", "ROK", "EMR", "FANUC", "KTOS", "YASKAWA", "IRBT",
    # AI Infrastructure
    "NVDA", "AMD", "AVGO", "QCOM", "INTC", "MU", "ASML",
    # Software/AI
    "PLTR", "PATH", "AI", "SNOW",
    # Nuclear
    "NEE", "DUK", "CEG", "VST", "SMR", "OKLO", "CCJ", "UEC", "UUUU",
]

# Real-world sleeve: Industrials, utilities, staples, energy - resilient cash flow
# Components from XLI, XLP, XLE, XLU
REALWORLD_UNIVERSE = [
    # Industrials (XLI)
    "CAT", "HON", "UPS", "BA", "RTX", "GE", "LMT", "MMM", "DE", "UNP",
    # Staples (XLP)
    "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "KMB", "GIS",
    # Energy (XLE)
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
    # Utilities (XLU)
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG", "ED", "XEL",
]

# Risk/Hedge sleeve: ETFs for portfolio optimization
RISK_UNIVERSE = [
    "SPY",   # S&P 500
    "IEF",   # 7-10Y Treasuries
    "TLT",   # 20+ Year Treasuries
    "XLV",   # Healthcare
    "XLU",   # Utilities
    "VNQ",   # Real Estate
    "IWD",   # Value
    "GLD",   # Gold
    "TIP",   # TIPS
    "LQD",   # Investment Grade Corp Bonds
]


def get_universe(sleeve: str) -> list[str]:
    """Get ticker universe for a sleeve."""
    universes = {
        "momentum": MOMENTUM_UNIVERSE,
        "futuristic": FUTURISTIC_UNIVERSE,
        "realworld": REALWORLD_UNIVERSE,
        "risk": RISK_UNIVERSE,
    }
    return universes.get(sleeve, [])


def get_all_tickers() -> list[str]:
    """Get all unique tickers across all sleeves."""
    all_tickers = set()
    all_tickers.update(MOMENTUM_UNIVERSE)
    all_tickers.update(FUTURISTIC_UNIVERSE)
    all_tickers.update(REALWORLD_UNIVERSE)
    all_tickers.update(RISK_UNIVERSE)
    return sorted(list(all_tickers))
