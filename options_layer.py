"""
Options Layer — Primary Execution Method
Mike trades options, not stock. This replaces stock buys with call options
on strong momentum signals. Stocks are a fallback only.

Strategy: buy slightly OTM calls (5% above price) with 2-3 week expiry.
This gives:
  - Leverage: small premium, big upside if stock moves
  - Defined risk: max loss = what you paid for the contract
  - Time to play out: 2-3 weeks is long enough for momentum to follow through

How Alpaca options work:
  - Find contracts via get_option_contracts() — search by underlying symbol
  - Each contract = 100 shares. Costs: premium * 100
  - Submit order using the OCC option symbol (e.g. NVDA250620C00900000)
  - Options require Alpaca account to have options trading enabled
"""
from alpaca.trading.requests import GetOptionContractsRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, ContractType
from alpaca_client import trading_client, get_equity
from config import MAX_POSITION_SIZE
from datetime import datetime, timedelta
import json, os

OPTIONS_LOG = "options_trades.json"

# Signal thresholds — only buy options on strong signals
MOMENTUM_THRESHOLD = 0.07      # 7%+ momentum on 10-day return
VOLUME_RATIO_THRESHOLD = 1.8   # 1.8x average volume = real conviction

# Contract selection — tuned to Mike's style (aggressive OTM, 2-3 months out)
from config import OPTIONS_OTM_PCT, OPTIONS_MIN_EXPIRY_DAYS, OPTIONS_MAX_EXPIRY_DAYS, OPTIONS_MAX_SPEND_PCT, OPTIONS_SCALE_OUT_LEVELS
OTM_PCT = OPTIONS_OTM_PCT
MIN_EXPIRY_DAYS = OPTIONS_MIN_EXPIRY_DAYS
MAX_EXPIRY_DAYS = OPTIONS_MAX_EXPIRY_DAYS

# Sizing — Mike concentrates, up to 15% per trade
MAX_OPTIONS_SPEND = OPTIONS_MAX_SPEND_PCT
MIN_CONTRACTS = 1
MAX_CONTRACTS = 50  # Mike bought 38 at once — allow concentration


def load_options_trades() -> list:
    if not os.path.exists(OPTIONS_LOG):
        return []
    with open(OPTIONS_LOG) as f:
        return json.load(f)


def save_options_trade(trade: dict):
    trades = load_options_trades()
    trades.append(trade)
    with open(OPTIONS_LOG, "w") as f:
        json.dump(trades, f, indent=2, default=str)


def find_call_contract(symbol: str, current_price: float) -> dict | None:
    """
    Finds the best call contract for a symbol.
    Targets: 5% OTM strike, 2-3 week expiry, highest open interest.
    Returns contract info dict or None if nothing suitable found.
    """
    target_strike = current_price * (1 + OTM_PCT)
    expiry_near = (datetime.now() + timedelta(days=MIN_EXPIRY_DAYS)).strftime("%Y-%m-%d")
    expiry_far  = (datetime.now() + timedelta(days=MAX_EXPIRY_DAYS)).strftime("%Y-%m-%d")

    # Search range: current price up to 15% OTM
    strike_min = str(round(current_price * 0.99, 2))
    strike_max = str(round(current_price * 1.15, 2))

    try:
        request = GetOptionContractsRequest(
            underlying_symbols=[symbol],
            contract_type=ContractType.CALL,
            expiration_date_gte=expiry_near,
            expiration_date_lte=expiry_far,
            strike_price_gte=strike_min,
            strike_price_lte=strike_max,
            limit=25
        )
        result = trading_client.get_option_contracts(request)

        if not result or not result.option_contracts:
            print(f"[OPTIONS] No contracts found for {symbol} in range ${strike_min}-${strike_max}")
            return None

        # Pick the contract with strike closest to our 5% OTM target
        best = min(
            result.option_contracts,
            key=lambda c: abs(float(c.strike_price) - target_strike)
        )

        return {
            "occ_symbol": best.symbol,
            "underlying": symbol,
            "strike": float(best.strike_price),
            "expiry": str(best.expiration_date),
            "type": "call",
            "otm_pct": round((float(best.strike_price) - current_price) / current_price * 100, 1)
        }

    except Exception as e:
        print(f"[OPTIONS] Contract search failed for {symbol}: {e}")
        return None


def calculate_contracts(equity: float) -> int:
    """
    How many contracts to buy based on account size.
    Capped at MAX_OPTIONS_SPEND % of equity / cost-per-contract.
    We use $5 as a conservative premium estimate since we don't have a quote yet.
    """
    max_spend = equity * MAX_OPTIONS_SPEND
    # Estimate ~$5 premium per share = $500 per contract. Adjust if needed.
    estimated_cost_per_contract = 500
    contracts = int(max_spend / estimated_cost_per_contract)
    return max(MIN_CONTRACTS, min(contracts, MAX_CONTRACTS))


def execute_options_buy(symbol: str, current_price: float, momentum: float, volume_ratio: float, reason: str) -> dict | None:
    """
    Main entry point. Call this instead of execute_buy() when signal is strong.
    Returns trade log dict if order placed, None if skipped or failed.

    momentum     — 10-day price return as a decimal (0.10 = 10%)
    volume_ratio — today's volume / 20-day avg volume
    """
    if momentum < MOMENTUM_THRESHOLD or volume_ratio < VOLUME_RATIO_THRESHOLD:
        return None

    contract = find_call_contract(symbol, current_price)
    if not contract:
        return None

    equity = get_equity()
    num_contracts = calculate_contracts(equity)

    try:
        order = trading_client.submit_order(
            MarketOrderRequest(
                symbol=contract["occ_symbol"],
                qty=num_contracts,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
        )

        trade = {
            "order_id": str(order.id),
            "underlying": symbol,
            "occ_symbol": contract["occ_symbol"],
            "strike": contract["strike"],
            "expiry": contract["expiry"],
            "otm_pct": contract["otm_pct"],
            "contracts": num_contracts,
            "underlying_price": current_price,
            "momentum_pct": round(momentum * 100, 2),
            "volume_ratio": round(volume_ratio, 2),
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "status": "open"
        }
        save_options_trade(trade)

        print(
            f"[OPTIONS] BUY {num_contracts}x {symbol} ${contract['strike']:.0f}C "
            f"exp {contract['expiry']} ({contract['otm_pct']:.1f}% OTM) | "
            f"Momentum {momentum*100:.1f}% | {volume_ratio:.1f}x vol | {reason}"
        )
        return trade

    except Exception as e:
        print(f"[OPTIONS] Order failed for {symbol}: {e}")
        return None


def is_strong_signal(momentum: float, volume_ratio: float) -> bool:
    """Quick check — is this signal strong enough to go options?"""
    return momentum >= MOMENTUM_THRESHOLD and volume_ratio >= VOLUME_RATIO_THRESHOLD


def get_open_options() -> list:
    """Returns all currently open options trades. Used by dashboard."""
    trades = load_options_trades()
    return [t for t in trades if t.get("status") == "open"]


def check_scale_outs():
    """
    Mike's strategy: sell portions as the trade moves in your favor.
    Sell 25% at +100%, another 25% at +200%, another 25% at +400%.
    Let the last 25% ride.

    Call this every scan cycle alongside check_stop_losses().
    """
    trades = load_options_trades()
    positions = {p.symbol: p for p in trading_client.get_all_positions()}

    scaled = 0
    for trade in trades:
        if trade.get("status") != "open":
            continue

        occ = trade.get("occ_symbol")
        if not occ or occ not in positions:
            continue

        position = positions[occ]
        entry_price = trade.get("entry_premium")
        if not entry_price:
            continue

        current_price = float(position.current_price)
        gain_pct = (current_price - entry_price) / entry_price * 100
        contracts_held = int(position.qty)
        already_scaled = trade.get("scale_outs_done", [])

        for level in OPTIONS_SCALE_OUT_LEVELS:
            target = level["at_gain_pct"]
            fraction = level["sell_fraction"]

            if gain_pct >= target and target not in already_scaled:
                contracts_to_sell = max(1, int(contracts_held * fraction))

                try:
                    from alpaca.trading.requests import MarketOrderRequest
                    from alpaca.trading.enums import OrderSide, TimeInForce
                    trading_client.submit_order(
                        MarketOrderRequest(
                            symbol=occ,
                            qty=contracts_to_sell,
                            side=OrderSide.SELL,
                            time_in_force=TimeInForce.DAY
                        )
                    )
                    if "scale_outs_done" not in trade:
                        trade["scale_outs_done"] = []
                    trade["scale_outs_done"].append(target)

                    print(
                        f"[SCALE OUT] {trade['underlying']} {occ} — "
                        f"sold {contracts_to_sell} contracts at +{gain_pct:.0f}% gain "
                        f"(target was +{target}%)"
                    )
                    scaled += 1
                except Exception as e:
                    print(f"[SCALE OUT] Failed for {occ}: {e}")

    if scaled:
        save_options_trades_list(trades)
    return scaled


def save_options_trades_list(trades: list):
    with open(OPTIONS_LOG, "w") as f:
        json.dump(trades, f, indent=2, default=str)
