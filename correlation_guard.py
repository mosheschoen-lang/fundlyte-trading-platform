"""
Correlation Guard
Prevents doubling up on stocks that move together.

Think of it like this: NVDA and AMD both make chips. If chip stocks drop,
they BOTH drop at the same time. Owning both = one big chip bet, not two separate bets.
This guard blocks the second trade in any correlated group.

Groups are based on sector + business model similarity.
"""
from alpaca_client import get_positions

# Each group = stocks that move together.
# Opening more than one from a group = doubled risk exposure.
CORRELATION_GROUPS = [
    {
        "name": "Semiconductors",
        "symbols": ["NVDA", "AMD", "INTC", "QCOM", "MU", "AVGO", "ARM"],
        "reason": "All chip stocks — move together on AI/chip demand news"
    },
    {
        "name": "Big Tech",
        "symbols": ["AAPL", "MSFT"],
        "reason": "Both mega-cap tech — highly correlated in risk-off moves"
    },
    {
        "name": "Mega Growth",
        "symbols": ["META", "GOOGL", "AMZN"],
        "reason": "Ad-revenue / cloud growth stocks — move together on macro"
    },
    {
        "name": "Broad Market ETFs",
        "symbols": ["SPY", "QQQ", "IWM", "DIA"],
        "reason": "Index ETFs — owning two is just a weighted S&P position"
    },
    {
        "name": "EV / Clean Energy",
        "symbols": ["TSLA", "RIVN", "LCID", "NIO"],
        "reason": "EV sentiment moves them together"
    },
]

# Max number of positions allowed from any single group at once
MAX_PER_GROUP = 1


def get_open_symbols() -> set:
    """Returns the set of stock symbols currently in open positions."""
    try:
        positions = get_positions()
        return {p.symbol for p in positions}
    except Exception as e:
        print(f"[CORR GUARD] Could not fetch positions: {e}")
        return set()


def check_correlation(symbol: str) -> dict:
    """
    Returns:
      allowed     — False = hard block
      blocked_by  — list of open symbols causing the block
      group       — name of the correlation group
      reason      — human-readable explanation

    Call before every buy order.
    """
    open_symbols = get_open_symbols()

    for group in CORRELATION_GROUPS:
        if symbol not in group["symbols"]:
            continue

        conflicts = [s for s in group["symbols"] if s in open_symbols and s != symbol]
        open_count = len(conflicts)

        if open_count >= MAX_PER_GROUP:
            return {
                "allowed": False,
                "blocked_by": conflicts,
                "group": group["name"],
                "reason": (
                    f"Correlation block: already holding {', '.join(conflicts)} "
                    f"({group['name']} group). {group['reason']}"
                )
            }

    return {
        "allowed": True,
        "blocked_by": [],
        "group": None,
        "reason": "No correlation conflicts"
    }


def get_correlation_summary() -> list:
    """Diagnostic — shows which groups have open positions. Used by dashboard."""
    open_symbols = get_open_symbols()
    summary = []
    for group in CORRELATION_GROUPS:
        open_in_group = [s for s in group["symbols"] if s in open_symbols]
        if open_in_group:
            summary.append({
                "group": group["name"],
                "open_positions": open_in_group,
                "at_limit": len(open_in_group) >= MAX_PER_GROUP
            })
    return summary
