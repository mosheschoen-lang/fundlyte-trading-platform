"""
Risk Manager — protects capital above all else.
Every trade must pass through here before execution.
"""
from alpaca_client import get_equity, get_positions, trading_client
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import MAX_RISK_PER_TRADE, MAX_POSITIONS, MAX_POSITION_SIZE
from volatility_filter import check_volatility
from correlation_guard import check_correlation
import json, os
from datetime import datetime

TRADE_LOG = "trades.json"

def load_trades():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG) as f:
            return json.load(f)
    return []

def save_trade(trade: dict):
    trades = load_trades()
    trades.append(trade)
    with open(TRADE_LOG, "w") as f:
        json.dump(trades, f, indent=2, default=str)

def can_trade() -> tuple[bool, str]:
    positions = get_positions()
    if len(positions) >= MAX_POSITIONS:
        return False, f"Max positions reached ({MAX_POSITIONS})"
    return True, "ok"

def calculate_shares(price: float, stop_loss: float) -> int:
    equity = get_equity()
    risk_amount = equity * MAX_RISK_PER_TRADE
    risk_per_share = price - stop_loss
    if risk_per_share <= 0:
        return 0
    shares = int(risk_amount / risk_per_share)
    # Cap at max position size
    max_shares = int((equity * MAX_POSITION_SIZE) / price)
    shares = min(shares, max_shares)
    return max(1, shares)

def execute_buy(symbol: str, price: float, stop_loss: float, take_profit: float, strategy: str, reason: str):
    allowed, msg = can_trade()
    if not allowed:
        print(f"[RISK] Trade blocked: {msg}")
        return None

    # Volatility filter — block if market or stock vol is too high
    vol_check = check_volatility(symbol)
    if not vol_check["allowed"]:
        print(f"[RISK] Volatility block on {symbol}: {vol_check['reason']}")
        return None
    if vol_check["caution"]:
        print(f"[RISK] Vol caution on {symbol}: {vol_check['reason']}")

    # Correlation guard — block if a correlated position is already open
    corr_check = check_correlation(symbol)
    if not corr_check["allowed"]:
        print(f"[RISK] Correlation block on {symbol}: {corr_check['reason']}")
        return None

    shares = calculate_shares(price, stop_loss)
    if shares == 0:
        print(f"[RISK] Trade blocked: position size too small")
        return None

    try:
        order = trading_client.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
        )
        trade = {
            "id": str(order.id),
            "symbol": symbol,
            "side": "buy",
            "shares": shares,
            "price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strategy": strategy,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "status": "open"
        }
        save_trade(trade)
        print(f"[TRADE] BUY {shares} {symbol} @ ${price:.2f} | Stop: ${stop_loss:.2f} | Target: ${take_profit:.2f}")
        return order
    except Exception as e:
        print(f"[ERROR] Order failed: {e}")
        return None

def execute_sell(symbol: str, reason: str):
    try:
        order = trading_client.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=None,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
        )
        print(f"[TRADE] SELL {symbol} | Reason: {reason}")
        return order
    except Exception as e:
        print(f"[ERROR] Sell failed: {e}")
        return None

def check_stop_losses():
    positions = get_positions()
    trades = load_trades()
    open_trades = {t["symbol"]: t for t in trades if t.get("status") == "open"}

    for position in positions:
        symbol = position.symbol
        current_price = float(position.current_price)
        if symbol in open_trades:
            trade = open_trades[symbol]
            stop = trade.get("stop_loss", 0)
            target = trade.get("take_profit", 999999)
            if current_price <= stop:
                print(f"[STOP LOSS] {symbol} hit stop at ${current_price:.2f}")
                execute_sell(symbol, f"Stop loss triggered at ${current_price:.2f}")
            elif current_price >= target:
                print(f"[TAKE PROFIT] {symbol} hit target at ${current_price:.2f}")
                execute_sell(symbol, f"Take profit hit at ${current_price:.2f}")
