"""
Kelly Criterion Position Sizer
Smarter than flat 2% risk — sizes positions based on your actual win rate
and average win/loss ratio. The more your strategy wins, the bigger it bets.

Kelly formula: f = W - (1-W)/R
  W = win rate, R = average win / average loss
Capped at half-Kelly (safer) and never exceeds our max position size.
"""
import json, os
from config import MAX_RISK_PER_TRADE, MAX_POSITION_SIZE

TRADE_LOG = "trades.json"

def load_trades():
    if not os.path.exists(TRADE_LOG):
        return []
    with open(TRADE_LOG) as f:
        return json.load(f)

def kelly_fraction(strategy: str = None, min_trades: int = 10) -> float:
    trades = load_trades()
    closed = [t for t in trades if t.get("status") == "closed" and t.get("pnl") is not None]

    if strategy:
        closed = [t for t in closed if t.get("strategy") == strategy]

    if len(closed) < min_trades:
        # Not enough data — use conservative default
        return MAX_RISK_PER_TRADE

    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]

    if not wins or not losses:
        return MAX_RISK_PER_TRADE

    win_rate = len(wins) / len(closed)
    avg_win = sum(t["pnl"] for t in wins) / len(wins)
    avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses))

    if avg_loss == 0:
        return MAX_RISK_PER_TRADE

    reward_risk_ratio = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / reward_risk_ratio

    # Half-Kelly for safety, capped at MAX_RISK_PER_TRADE * 3
    half_kelly = kelly / 2
    capped = min(half_kelly, MAX_RISK_PER_TRADE * 3)
    floored = max(capped, 0.005)  # minimum 0.5% risk

    return round(floored, 4)

def kelly_shares(price: float, stop_loss: float, equity: float, strategy: str = None) -> int:
    frac = kelly_fraction(strategy)
    risk_amount = equity * frac
    risk_per_share = price - stop_loss

    if risk_per_share <= 0:
        return 0

    shares = int(risk_amount / risk_per_share)
    max_shares = int((equity * MAX_POSITION_SIZE) / price)
    shares = min(shares, max_shares)
    return max(1, shares)
