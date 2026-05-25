"""
Mean Reversion Strategy (Bollinger Bands)
Buy when price touches lower band + RSI oversold.
Sell when price reaches middle band or upper band.
Best for sideways/consolidating markets.
"""
import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca_client import stock_data_client

def get_signal(symbol: str, is_crypto: bool = False) -> dict:
    end = datetime.now()
    start = end - timedelta(days=45)

    try:
        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Hour, start=start, end=end)
        bars = stock_data_client.get_stock_bars(request).df

        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs(symbol, level=0)

        if len(bars) < 25:
            return {"signal": "hold", "reason": "not enough data"}

        close = bars["close"]

        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper_band = sma20 + (2 * std20)
        lower_band = sma20 - (2 * std20)

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_price = float(close.iloc[-1])
        lower = float(lower_band.iloc[-1])
        upper = float(upper_band.iloc[-1])
        middle = float(sma20.iloc[-1])
        current_rsi = float(rsi.iloc[-1])

        # Buy: price at or below lower band + RSI oversold
        if current_price <= lower * 1.005 and current_rsi < 35:
            stop_loss = current_price * 0.97
            take_profit = middle  # target: mean reversion back to middle
            return {
                "signal": "buy",
                "price": current_price,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "rsi": round(current_rsi, 2),
                "reason": f"Oversold at lower band, RSI {current_rsi:.1f}"
            }

        # Sell: price reached upper band or RSI overbought
        if current_price >= upper * 0.995 or current_rsi > 70:
            return {
                "signal": "sell",
                "price": current_price,
                "rsi": round(current_rsi, 2),
                "reason": f"Upper band reached or RSI overbought {current_rsi:.1f}"
            }

        return {"signal": "hold", "price": current_price, "rsi": round(current_rsi, 2), "reason": "price within bands"}

    except Exception as e:
        return {"signal": "error", "reason": str(e)}
