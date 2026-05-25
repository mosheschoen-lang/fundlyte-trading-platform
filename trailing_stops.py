"""
Trailing Stop Manager
As price rises, the stop loss automatically moves up to lock in gains.
Example: buy at $100, stop at $97. Price rises to $110 → stop moves to $106.70.
This lets winners run while protecting profits.
"""
import json, os
from datetime import datetime
from alpaca_client import get_positions

TRADE_LOG = "trades.json"

def load_trades():
    if not os.path.exists(TRADE_LOG):
        return []
    with open(TRADE_LOG) as f:
        return json.load(f)

def save_trades(trades):
    with open(TRADE_LOG, "w") as f:
        json.dump(trades, f, indent=2, default=str)

def update_trailing_stops(trail_pct: float = 0.03):
    """
    trail_pct = how far below the high to set the stop.
    Default 3% — if price hits $110, stop is at $106.70.
    """
    trades = load_trades()
    positions = get_positions()
    position_map = {p.symbol: float(p.current_price) for p in positions}

    updated = 0
    for trade in trades:
        if trade.get("status") != "open":
            continue
        symbol = trade.get("symbol")
        if symbol not in position_map:
            continue

        current_price = position_map[symbol]
        current_stop = trade.get("stop_loss", 0)
        current_high = trade.get("price_high", trade.get("price", current_price))

        # Track the highest price seen
        new_high = max(current_high, current_price)
        trade["price_high"] = new_high

        # Trailing stop = highest price * (1 - trail_pct)
        new_stop = round(new_high * (1 - trail_pct), 4)

        # Only move stop UP, never down
        if new_stop > current_stop:
            print(f"[TRAIL] {symbol}: stop moved ${current_stop:.2f} → ${new_stop:.2f} (high: ${new_high:.2f})")
            trade["stop_loss"] = new_stop
            trade["stop_updated_at"] = datetime.now().isoformat()
            updated += 1

    if updated:
        save_trades(trades)
        print(f"[TRAIL] Updated {updated} trailing stop(s)")

    return updated
