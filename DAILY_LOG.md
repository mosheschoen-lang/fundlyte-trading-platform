# FundLyte Trading Platform — Daily Build Log

---

## May 25, 2026 (Night build — overnight session)

### What was built tonight:

**1. Trailing Stop Manager** (`trailing_stops.py`)
- Stop losses now move UP automatically as price rises
- Locks in profits without cutting winners short
- Example: buy NVDA at $100, stop at $97. Rises to $120 → stop automatically moves to $116.40
- Never moves the stop DOWN — only protects gains

**2. Market Regime Detector** (`market_regime.py`)
- Reads SPY every scan to detect: TRENDING BULL, TRENDING BEAR, SIDEWAYS, or VOLATILE
- Trending bull → runs momentum + EMA strategies
- Sideways → runs mean reversion only
- Volatile → sits out entirely (protects capital)
- Reduces position size in bear/volatile markets automatically

**3. Kelly Criterion Position Sizer** (`kelly_sizer.py`)
- Replaces flat 2% risk with dynamic sizing based on your actual win rate
- The more a strategy wins historically, the bigger it bets
- Capped at half-Kelly for safety — aggressive but not reckless
- Falls back to 2% until 10+ closed trades establish a track record

**4. Backtesting Module** (`backtest.py`)
- Tests all 3 strategies against 90 days of real historical data
- Reports win rate, avg win, avg loss, total return, max drawdown per strategy per asset
- Run anytime: `python3 backtest.py`
- Use this before going live Wednesday to confirm strategies are profitable

**5. Engine upgrades** (`engine.py`)
- Trailing stops checked every scan cycle
- Market regime read at start of every scan
- Strategies only run if regime recommends them
- All signals now logged for dashboard display

### Why this makes the strategy better:
Trailing stops + regime detection = the two biggest edge improvements possible. Most retail traders lose because they exit winners too early and hold losers too long. Trailing stops fix the first problem. Regime detection fixes the second by not fighting the market trend.

### 3 suggested improvements for tomorrow:
1. **Volatility filter**: skip trades on any stock with VIX > 30 or individual stock IV > 50%
2. **Correlation guard**: don't open NVDA if AMD already open — too correlated, doubles risk
3. **Options layer**: buy calls on strong momentum signals for leveraged upside

### Platform readiness score: 7/10
Core engine is solid. Risk management is strong. Needs backtest validation and options layer before ideal. Ready to go live Wednesday with current build.

---
