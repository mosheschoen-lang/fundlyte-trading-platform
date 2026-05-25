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

CRYPTO_WATCHLIST = [
    "BTC/USD", "ETH/USD", "SOL/USD"
]
