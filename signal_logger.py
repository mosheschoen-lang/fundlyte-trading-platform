"""
Logs all signals to signals.json so the dashboard can display them.
"""
import json, os
from datetime import datetime

SIGNAL_LOG = "signals.json"
MAX_SIGNALS = 200

def log_signal(symbol: str, strategy: str, signal: str, reason: str, price: float = None):
    signals = []
    if os.path.exists(SIGNAL_LOG):
        with open(SIGNAL_LOG) as f:
            signals = json.load(f)

    signals.append({
        "symbol": symbol,
        "strategy": strategy,
        "signal": signal,
        "reason": reason,
        "price": price,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    # Keep only last 200 signals
    signals = signals[-MAX_SIGNALS:]

    with open(SIGNAL_LOG, "w") as f:
        json.dump(signals, f, indent=2, default=str)
