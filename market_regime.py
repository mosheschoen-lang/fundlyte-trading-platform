"""
Market Regime Detector
Detects whether the market is TRENDING or SIDEWAYS.
- Trending: use momentum + EMA crossover strategies
- Sideways: use mean reversion strategy
- Bearish: reduce position sizes, avoid new longs

Uses SPY (S&P 500 ETF) as the market barometer.
"""
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca_client import stock_data_client
import pandas as pd

def get_market_regime() -> dict:
    end = datetime.now()
    start = end - timedelta(days=60)

    try:
        request = StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Day, start=start, end=end)
        bars = stock_data_client.get_stock_bars(request).df

        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs("SPY", level=0)

        if len(bars) < 30:
            return {"regime": "unknown", "confidence": 0, "reason": "not enough data"}

        close = bars["close"]

        # ADX-style directional movement
        ema20 = close.ewm(span=20).mean()
        ema50 = close.ewm(span=50).mean()

        current = float(close.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])

        # 20-day return
        ret_20 = (current - float(close.iloc[-20])) / float(close.iloc[-20])

        # Volatility (std dev of daily returns)
        daily_returns = close.pct_change().dropna()
        vol_20 = float(daily_returns.tail(20).std())

        # Regime logic
        trending_up = e20 > e50 and current > e20 and ret_20 > 0.02
        trending_down = e20 < e50 and current < e20 and ret_20 < -0.02
        high_volatility = vol_20 > 0.015  # >1.5% daily vol = choppy

        if trending_up and not high_volatility:
            regime = "trending_bull"
            recommended = ["ema_crossover", "momentum"]
            size_multiplier = 1.0
            reason = f"SPY trending up {ret_20*100:.1f}%, EMA20 > EMA50, low vol"

        elif trending_down and not high_volatility:
            regime = "trending_bear"
            recommended = ["mean_reversion"]
            size_multiplier = 0.5  # half size in bear market
            reason = f"SPY trending down {ret_20*100:.1f}%, EMA20 < EMA50"

        elif high_volatility:
            regime = "volatile"
            recommended = []  # sit out extreme volatility
            size_multiplier = 0.25
            reason = f"High volatility {vol_20*100:.2f}% daily std — reducing size"

        else:
            regime = "sideways"
            recommended = ["mean_reversion"]
            size_multiplier = 0.75
            reason = f"SPY sideways, {ret_20*100:.1f}% 20-day return"

        return {
            "regime": regime,
            "recommended_strategies": recommended,
            "size_multiplier": size_multiplier,
            "spy_return_20d": round(ret_20 * 100, 2),
            "daily_volatility": round(vol_20 * 100, 2),
            "reason": reason
        }

    except Exception as e:
        return {"regime": "unknown", "recommended_strategies": ["ema_crossover", "momentum", "mean_reversion"], "size_multiplier": 1.0, "reason": str(e)}
