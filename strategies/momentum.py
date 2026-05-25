"""
Momentum + Volume Breakout Strategy
Buy when price breaks above 20-day high with above-average volume.
High quality setups only — looks for strong trending stocks.
"""
import pandas as pd
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca_client import stock_data_client, crypto_data_client

def get_signal(symbol: str, is_crypto: bool = False) -> dict:
    end = datetime.now()
    start = end - timedelta(days=60)

    try:
        if is_crypto:
            request = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=start, end=end)
            bars = crypto_data_client.get_crypto_bars(request).df
        else:
            request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=start, end=end)
            bars = stock_data_client.get_stock_bars(request).df

        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs(symbol, level=0)

        if len(bars) < 22:
            return {"signal": "hold", "reason": "not enough data"}

        close = bars["close"]
        volume = bars["volume"]
        high = bars["high"]

        rolling_high = high.rolling(20).max()
        avg_volume = volume.rolling(20).mean()

        current_price = float(close.iloc[-1])
        current_volume = float(volume.iloc[-1])
        prev_high = float(rolling_high.iloc[-2])
        avg_vol = float(avg_volume.iloc[-1])

        # ADX-style trend strength using price range
        atr = (bars["high"] - bars["low"]).rolling(14).mean().iloc[-1]
        trend_strength = atr / current_price

        # Breakout: price breaks 20-day high with 1.5x average volume
        breakout = current_price > prev_high and current_volume > avg_vol * 1.5

        # Momentum: 10-day return > 5%
        momentum = (current_price - float(close.iloc[-10])) / float(close.iloc[-10])

        if breakout and momentum > 0.05:
            stop_loss = current_price * 0.95
            take_profit = current_price * 1.10
            return {
                "signal": "buy",
                "price": current_price,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "momentum": round(momentum * 100, 2),
                "volume_ratio": round(current_volume / avg_vol, 2),
                "reason": f"Breakout with {momentum*100:.1f}% momentum, {current_volume/avg_vol:.1f}x volume"
            }

        # Exit: momentum fading — price drops below 10-day MA
        ma10 = close.rolling(10).mean().iloc[-1]
        if current_price < ma10 * 0.98:
            return {
                "signal": "sell",
                "price": current_price,
                "reason": "Price fell below 10-day MA — momentum fading"
            }

        return {"signal": "hold", "price": current_price, "momentum": round(momentum * 100, 2), "reason": "no breakout"}

    except Exception as e:
        return {"signal": "error", "reason": str(e)}
