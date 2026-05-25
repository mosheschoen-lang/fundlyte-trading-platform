"""
Benchmark Tracker — grades each strategy.
A strategy must pass ALL benchmarks before capital scales up.
"""
import json, os
from config import (BENCHMARK_MIN_WIN_RATE, BENCHMARK_MAX_DRAWDOWN,
                    BENCHMARK_MIN_TRADES, BENCHMARK_MIN_RETURN, CAPITAL_TIERS)

TRADE_LOG = "trades.json"
BENCHMARK_LOG = "benchmarks.json"

def load_trades():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG) as f:
            return json.load(f)
    return []

def calculate_metrics(strategy: str = None) -> dict:
    trades = load_trades()
    if strategy:
        trades = [t for t in trades if t.get("strategy") == strategy]

    closed = [t for t in trades if t.get("status") == "closed"]
    if not closed:
        return {"trades": 0, "win_rate": 0, "net_return": 0, "max_drawdown": 0, "passed": False}

    wins = [t for t in closed if t.get("pnl", 0) > 0]
    win_rate = len(wins) / len(closed)
    net_return = sum(t.get("pnl", 0) for t in closed)

    # Max drawdown from trade PnL sequence
    equity_curve = []
    running = 0
    for t in closed:
        running += t.get("pnl", 0)
        equity_curve.append(running)

    peak = 0
    max_drawdown = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        drawdown = (peak - val) / peak if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    total_invested = sum(t.get("price", 0) * t.get("shares", 0) for t in closed)
    pct_return = net_return / total_invested if total_invested > 0 else 0

    passed = (
        len(closed) >= BENCHMARK_MIN_TRADES and
        win_rate >= BENCHMARK_MIN_WIN_RATE and
        max_drawdown <= BENCHMARK_MAX_DRAWDOWN and
        pct_return >= BENCHMARK_MIN_RETURN
    )

    return {
        "strategy": strategy or "all",
        "trades": len(closed),
        "win_rate": round(win_rate, 4),
        "net_pnl": round(net_return, 2),
        "pct_return": round(pct_return * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "passed": passed
    }

def get_current_tier(metrics: dict) -> dict:
    tier_index = 0
    if metrics["passed"]:
        tier_index = min(tier_index + 1, len(CAPITAL_TIERS) - 1)

    return {
        "tier": tier_index + 1,
        "capital": CAPITAL_TIERS[tier_index],
        "next_tier": CAPITAL_TIERS[tier_index + 1] if tier_index + 1 < len(CAPITAL_TIERS) else None
    }

def print_report():
    metrics = calculate_metrics()
    print("\n===== BENCHMARK REPORT =====")
    print(f"Total closed trades : {metrics['trades']}")
    print(f"Win rate            : {metrics['win_rate']*100:.1f}% (need 55%+)")
    print(f"Net P&L             : ${metrics['net_pnl']:.2f}")
    print(f"Return              : {metrics['pct_return']:.2f}% (need 2%+)")
    print(f"Max drawdown        : {metrics['max_drawdown']:.2f}% (need <15%)")
    print(f"PASSED              : {'✅ YES' if metrics['passed'] else '❌ NOT YET'}")
    print("============================\n")
    return metrics
