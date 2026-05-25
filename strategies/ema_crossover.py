"""
EMA Crossover Strategy
Buy when 9 EMA crosses above 21 EMA with RSI confirmation.
Sell when 9 EMA crosses below 21 EMA or stop loss hit.
"""
import pandas as pd
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca_client import stock_data_client, crypto_data_client

def get_signal(symbol: str, is_crypto: bool = False) -> dict:
    end = datetime.now()
    start = end - timedelta(days=30)

    try:
        if is_crypto:
            request = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Hour, start=start, end=end)
            bars = crypto_data_client.get_crypto_bars(request).df
        else:
            request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Hour, start=start, end=end)
            bars = stock_data_client.get_stock_bars(request).df

        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs(symbol, level=0)

        if len(bars) < 25:
            return {"signal": "hold", "reason": "not enough data"}

        close = bars["close"]
        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]
        prev_cross = ema9.iloc[-2] <= ema21.iloc[-2]
        curr_cross = ema9.iloc[-1] > ema21.iloc[-1]
        bullish_cross = prev_cross and curr_cross

        prev_death = ema9.iloc[-2] >= ema21.iloc[-2]
        curr_death = ema9.iloc[-1] < ema21.iloc[-1]
        bearish_cross = prev_death and curr_death

        current_price = float(close.iloc[-1])

        if bullish_cross and current_rsi < 70:
            stop_loss = current_price * 0.97  # 3% stop loss
            take_profit = current_price * 1.06  # 6% target
            return {
                "signal": "buy",
                "price": current_price,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "rsi": round(current_rsi, 2),
                "reason": f"EMA crossover bullish, RSI {current_rsi:.1f}"
            }
        elif bearish_cross or current_rsi > 75:
            return {
                "signal": "sell",
                "price": current_price,
                "rsi": round(current_rsi, 2),
                "reason": f"EMA bearish cross or RSI overbought {current_rsi:.1f}"
            }
        else:
            return {"signal": "hold", "price": current_price, "rsi": round(current_rsi, 2), "reason": "no signal"}

    except Exception as e:
        return {"signal": "error", "reason": str(e)}
