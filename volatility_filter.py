"""
Volatility Filter
Protects against trading in dangerous market conditions.

For options buyers (like Mike), high volatility = expensive premiums = bad risk/reward.
Uses SPY historical vol as a VIX proxy — no extra API calls.

Thresholds (annualized SPY vol maps roughly 1:1 to VIX):
  > 30% = BLOCK  (VIX ~30 equivalent — panic mode)
  > 20% = CAUTION — still trade but reduce size
  > 60% individual stock vol = BLOCK options on that stock (premium too expensive)
  > 40% individual stock vol = CAUTION
"""
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca_client import stock_data_client
import pandas as pd

# VIX proxy thresholds (SPY annualized vol ≈ VIX level)
VIX_BLOCK = 0.30       # block all trades — market in panic
VIX_CAUTION = 0.20     # reduce size — elevated fear

# Individual stock vol thresholds (annualized)
STOCK_VOL_BLOCK = 0.60    # options premiums are too expensive
STOCK_VOL_CAUTION = 0.40  # premiums elevated, flag it


def _get_annualized_vol(symbol: str, lookback_days: int = 40) -> float:
    """Calculate annualized historical volatility for any symbol."""
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    try:
        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=start, end=end)
        bars = stock_data_client.get_stock_bars(request).df
        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs(symbol, level=0)
        daily_returns = bars["close"].pct_change().dropna()
        daily_vol = float(daily_returns.tail(20).std())
        return round(daily_vol * (252 ** 0.5), 4)
    except Exception as e:
        print(f"[VOL FILTER] Could not get vol for {symbol}: {e}")
        return 0.25  # assume moderate if fetch fails


def get_vix_proxy() -> float:
    """SPY 20-day annualized vol — our stand-in for VIX."""
    return _get_annualized_vol("SPY")


def check_volatility(symbol: str) -> dict:
    """
    Run before every trade. Returns:
      allowed  — False = hard block, do not trade
      caution  — True = trade allowed but reduce size
      vix_proxy — SPY annualized vol (VIX equivalent)
      stock_vol — individual stock annualized vol
      reason   — human-readable explanation
    """
    vix_proxy = get_vix_proxy()
    stock_vol = _get_annualized_vol(symbol)

    # Hard block conditions
    if vix_proxy >= VIX_BLOCK:
        return {
            "allowed": False,
            "caution": False,
            "vix_proxy": round(vix_proxy * 100, 1),
            "stock_vol": round(stock_vol * 100, 1),
            "reason": f"Market vol {vix_proxy*100:.0f}% (VIX ~{vix_proxy*100:.0f}) — panic mode, sitting out"
        }

    if stock_vol >= STOCK_VOL_BLOCK:
        return {
            "allowed": False,
            "caution": False,
            "vix_proxy": round(vix_proxy * 100, 1),
            "stock_vol": round(stock_vol * 100, 1),
            "reason": f"{symbol} vol {stock_vol*100:.0f}% — options premiums too expensive to buy"
        }

    # Caution conditions
    caution = vix_proxy >= VIX_CAUTION or stock_vol >= STOCK_VOL_CAUTION
    reasons = []
    if vix_proxy >= VIX_CAUTION:
        reasons.append(f"market vol elevated {vix_proxy*100:.0f}%")
    if stock_vol >= STOCK_VOL_CAUTION:
        reasons.append(f"{symbol} vol {stock_vol*100:.0f}% — premiums elevated")

    return {
        "allowed": True,
        "caution": caution,
        "vix_proxy": round(vix_proxy * 100, 1),
        "stock_vol": round(stock_vol * 100, 1),
        "reason": " | ".join(reasons) if reasons else f"Market vol {vix_proxy*100:.0f}%, {symbol} vol {stock_vol*100:.0f}% — conditions ok"
    }
