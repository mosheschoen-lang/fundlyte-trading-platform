"""
Main Trading Engine — runs all strategies on a schedule.
Checks signals every 15 minutes during market hours.
"""
from strategies.ema_crossover import get_signal as ema_signal
from strategies.momentum import get_signal as momentum_signal
from strategies.mean_reversion import get_signal as reversion_signal
from risk_manager import execute_buy, execute_sell, check_stop_losses
from benchmark import print_report
from trailing_stops import update_trailing_stops
from market_regime import get_market_regime
from signal_logger import log_signal
from config import STOCK_WATCHLIST, CRYPTO_WATCHLIST
from alpaca_client import get_account
from datetime import datetime
import time

def is_market_open() -> bool:
    from alpaca_client import trading_client
    clock = trading_client.get_clock()
    return clock.is_open

def run_strategies():
    print(f"\n[ENGINE] Scanning at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    check_stop_losses()
    update_trailing_stops()

    regime = get_market_regime()
    print(f"[REGIME] {regime['regime'].upper()} — {regime['reason']}")
    active_strategies = regime.get("recommended_strategies", ["ema_crossover", "momentum", "mean_reversion"])
    size_mult = regime.get("size_multiplier", 1.0)

    if not active_strategies:
        print(f"[REGIME] High volatility — sitting out. No new trades.")
        return

    # Run EMA Crossover on all stocks
    if "ema_crossover" in active_strategies:
        for symbol in STOCK_WATCHLIST:
            signal = ema_signal(symbol)
            log_signal(symbol, "ema_crossover", signal["signal"], signal.get("reason",""), signal.get("price"))
            if signal["signal"] == "buy":
                print(f"[EMA] BUY signal: {symbol} — {signal['reason']}")
                execute_buy(symbol=symbol, price=signal["price"], stop_loss=signal["stop_loss"],
                            take_profit=signal["take_profit"], strategy="ema_crossover", reason=signal["reason"])
            elif signal["signal"] == "sell":
                print(f"[EMA] SELL signal: {symbol} — {signal['reason']}")
                execute_sell(symbol, signal["reason"])
            time.sleep(0.3)

    # Run Momentum on all stocks
    if "momentum" in active_strategies:
        for symbol in STOCK_WATCHLIST:
            signal = momentum_signal(symbol)
            log_signal(symbol, "momentum", signal["signal"], signal.get("reason",""), signal.get("price"))
            if signal["signal"] == "buy":
                print(f"[MOMENTUM] BUY signal: {symbol} — {signal['reason']}")
                execute_buy(symbol=symbol, price=signal["price"], stop_loss=signal["stop_loss"],
                            take_profit=signal["take_profit"], strategy="momentum", reason=signal["reason"])
            time.sleep(0.3)

    # Run Mean Reversion on stocks
    if "mean_reversion" in active_strategies:
        for symbol in ["AAPL", "MSFT", "AMZN", "SPY", "QQQ"]:
            signal = reversion_signal(symbol)
            log_signal(symbol, "mean_reversion", signal["signal"], signal.get("reason",""), signal.get("price"))
            if signal["signal"] == "buy":
                print(f"[REVERSION] BUY signal: {symbol} — {signal['reason']}")
                execute_buy(symbol=symbol, price=signal["price"], stop_loss=signal["stop_loss"],
                            take_profit=signal["take_profit"], strategy="mean_reversion", reason=signal["reason"])
            time.sleep(0.3)

    # Run EMA on crypto (24/7)
    for symbol in CRYPTO_WATCHLIST:
        signal = ema_signal(symbol, is_crypto=True)
        if signal["signal"] == "buy":
            print(f"[CRYPTO EMA] BUY signal: {symbol} — {signal['reason']}")
        time.sleep(0.3)

    print_report()

def run(interval_minutes: int = 15):
    print(f"[ENGINE] Starting — scanning every {interval_minutes} minutes")
    account = get_account()
    print(f"[ENGINE] Account equity: ${float(account.equity):,.2f}")
    print(f"[ENGINE] Buying power:   ${float(account.buying_power):,.2f}")

    while True:
        try:
            if is_market_open():
                run_strategies()
            else:
                # Crypto runs 24/7 even when market is closed
                print(f"[ENGINE] Market closed — scanning crypto only")
                for symbol in CRYPTO_WATCHLIST:
                    signal = ema_signal(symbol, is_crypto=True)
                    if signal["signal"] == "buy":
                        print(f"[CRYPTO] BUY signal: {symbol}")
        except Exception as e:
            print(f"[ERROR] Engine error: {e}")

        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    run()
