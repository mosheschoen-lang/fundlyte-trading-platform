"""
Backtesting Module
Tests strategies against 90 days of real historical data BEFORE risking real money.
Shows win rate, max drawdown, and total return for each strategy on each asset.
Run this to see how strategies would have performed.
"""
import pandas as pd
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca_client import stock_data_client, crypto_data_client
from config import STOCK_WATCHLIST, CRYPTO_WATCHLIST

def fetch_bars(symbol: str, days: int = 90, is_crypto: bool = False) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        if is_crypto:
            req = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Hour, start=start, end=end)
            df = crypto_data_client.get_crypto_bars(req).df
        else:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Hour, start=start, end=end)
            df = stock_data_client.get_stock_bars(req).df

        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)
        return df
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return pd.DataFrame()

def backtest_ema(df: pd.DataFrame) -> dict:
    if len(df) < 30:
        return {}
    close = df["close"]
    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / loss))

    trades = []
    in_trade = False
    entry = 0

    for i in range(22, len(close)):
        prev_cross = ema9.iloc[i-1] <= ema21.iloc[i-1]
        curr_cross = ema9.iloc[i] > ema21.iloc[i]
        bullish = prev_cross and curr_cross and rsi.iloc[i] < 70

        prev_death = ema9.iloc[i-1] >= ema21.iloc[i-1]
        curr_death = ema9.iloc[i] < ema21.iloc[i]
        bearish = prev_death and curr_death

        if bullish and not in_trade:
            entry = float(close.iloc[i])
            stop = entry * 0.97
            in_trade = True
        elif in_trade:
            current = float(close.iloc[i])
            if bearish or current <= stop or current >= entry * 1.06:
                pnl_pct = (current - entry) / entry * 100
                trades.append(pnl_pct)
                in_trade = False

    return _summarize(trades, "ema_crossover")

def backtest_momentum(df: pd.DataFrame) -> dict:
    if len(df) < 22:
        return {}
    close = df["close"]
    high = df["high"]
    volume = df["volume"]
    rolling_high = high.rolling(20).max()
    avg_vol = volume.rolling(20).mean()

    trades = []
    in_trade = False
    entry = 0
    stop = 0

    for i in range(21, len(close)):
        current = float(close.iloc[i])
        prev_high = float(rolling_high.iloc[i-1])
        vol_ratio = float(volume.iloc[i]) / float(avg_vol.iloc[i]) if avg_vol.iloc[i] > 0 else 0
        momentum = (current - float(close.iloc[i-10])) / float(close.iloc[i-10]) if i >= 10 else 0

        if not in_trade and current > prev_high and vol_ratio > 1.5 and momentum > 0.05:
            entry = current
            stop = entry * 0.95
            in_trade = True
        elif in_trade:
            ma10 = float(close.iloc[max(0,i-10):i].mean())
            if current <= stop or current <= ma10 * 0.98 or current >= entry * 1.10:
                pnl_pct = (current - entry) / entry * 100
                trades.append(pnl_pct)
                in_trade = False

    return _summarize(trades, "momentum")

def backtest_mean_reversion(df: pd.DataFrame) -> dict:
    if len(df) < 25:
        return {}
    close = df["close"]
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    lower = sma20 - 2 * std20
    upper = sma20 + 2 * std20
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / loss))

    trades = []
    in_trade = False
    entry = 0

    for i in range(25, len(close)):
        current = float(close.iloc[i])
        lb = float(lower.iloc[i])
        ub = float(upper.iloc[i])
        mid = float(sma20.iloc[i])
        r = float(rsi.iloc[i])

        if not in_trade and current <= lb * 1.005 and r < 35:
            entry = current
            stop = entry * 0.97
            in_trade = True
        elif in_trade:
            if current <= stop or current >= ub * 0.995 or r > 70:
                pnl_pct = (current - entry) / entry * 100
                trades.append(pnl_pct)
                in_trade = False

    return _summarize(trades, "mean_reversion")

def _summarize(trades: list, name: str) -> dict:
    if not trades:
        return {"strategy": name, "trades": 0}
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    total = sum(trades)
    equity = [0]
    running = 0
    for t in trades:
        running += t
        equity.append(running)
    peak = 0
    max_dd = 0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v)
        if dd > max_dd:
            max_dd = dd
    return {
        "strategy": name,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        "total_return": round(total, 2),
        "max_drawdown": round(max_dd, 2)
    }

def run_backtest(symbols: list = None, is_crypto: bool = False):
    symbols = symbols or (CRYPTO_WATCHLIST if is_crypto else STOCK_WATCHLIST[:5])
    print(f"\n{'='*60}")
    print(f"BACKTEST — {'CRYPTO' if is_crypto else 'STOCKS'} — 90 days")
    print(f"{'='*60}")

    all_results = []
    for symbol in symbols:
        print(f"\n  {symbol}")
        df = fetch_bars(symbol, 90, is_crypto)
        if df.empty:
            continue
        for fn in [backtest_ema, backtest_momentum, backtest_mean_reversion]:
            result = fn(df)
            if result and result.get("trades", 0) > 0:
                result["symbol"] = symbol
                all_results.append(result)
                wr = result.get("win_rate", 0)
                tr = result.get("total_return", 0)
                trades = result.get("trades", 0)
                print(f"    {result['strategy']:20s} | {trades:3d} trades | WR {wr:5.1f}% | Return {tr:+.1f}%")

    print(f"\n{'='*60}")
    if all_results:
        best = max(all_results, key=lambda x: x.get("total_return", 0))
        print(f"BEST STRATEGY: {best['strategy']} on {best['symbol']} — {best['total_return']:+.1f}% return, {best['win_rate']}% win rate")
    print(f"{'='*60}\n")
    return all_results

if __name__ == "__main__":
    run_backtest(["AAPL", "NVDA", "TSLA", "SPY"])
    run_backtest(["BTC/USD", "ETH/USD"], is_crypto=True)
