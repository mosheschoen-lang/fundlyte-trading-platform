import os
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

IS_PAPER = "paper" in ALPACA_BASE_URL

# Capital tiers - staged deployment
CAPITAL_TIERS = [200, 500, 1100]  # $1,800 total
CURRENT_TIER = 0

# Risk management
MAX_RISK_PER_TRADE = 0.02       # 2% of account per trade
MAX_POSITIONS = 3               # max open trades at once
MAX_POSITION_SIZE = 0.25        # max 25% of capital in one position

# Benchmark gates (must pass ALL to scale up)
BENCHMARK_MIN_WIN_RATE = 0.55   # 55% win rate
BENCHMARK_MAX_DRAWDOWN = 0.15   # 15% max drawdown
BENCHMARK_MIN_TRADES = 10       # minimum trades before evaluating
BENCHMARK_MIN_RETURN = 0.02     # 2% net return

# Assets to trade
STOCK_WATCHLIST = [
    "AAPL", "NVDA", "TSLA", "MSFT", "AMZN",
    "META", "GOOGL", "AMD", "SPY", "QQQ"
]

# Speculative high-momentum tickers — Mike's actual trading style
# These are low-price, high-leverage plays. Cheap OTM calls can 10x on big moves.
SPECULATIVE_WATCHLIST = [
    "SPCE",   # Virgin Galactic — Mike's biggest trade, already profitable
    "ASTS",   # AST SpaceMobile — space/tech momentum
    "IONQ",   # Quantum computing momentum
    "RKLB",   # Rocket Lab — space sector
    "LUNR",   # Intuitive Machines — space sector
    "ACHR",   # Archer Aviation — eVTOL momentum
]

CRYPTO_WATCHLIST = [
    "BTC/USD", "ETH/USD", "SOL/USD"
]

# Options settings — tuned to Mike's actual style
# He buys cheap OTM calls 2-4 months out on speculative/momentum names
OPTIONS_OTM_PCT = 0.15            # 15% OTM — aggressive, cheap premium, big leverage
OPTIONS_MIN_EXPIRY_DAYS = 30      # at least 1 month out
OPTIONS_MAX_EXPIRY_DAYS = 90      # up to 3 months out (like April → July)
OPTIONS_MAX_SPEND_PCT = 0.15      # up to 15% of account on one options trade (Mike concentrates)
OPTIONS_SCALE_OUT_LEVELS = [      # sell portions as premium multiplies
    {"at_gain_pct": 100, "sell_fraction": 0.25},   # +100% → sell 25%
    {"at_gain_pct": 200, "sell_fraction": 0.25},   # +200% → sell another 25%
    {"at_gain_pct": 400, "sell_fraction": 0.25},   # +400% → sell another 25%
    # last 25% rides to expiry or max pain
]
