"""
Flask dashboard server — shows live trading data.
Access at http://localhost:5001 on computer or phone (same WiFi).
"""
from flask import Flask, render_template, jsonify
from alpaca_client import trading_client, get_account, get_positions
from benchmark import calculate_metrics, get_current_tier
import json, os

app = Flask(__name__)

TRADE_LOG = "trades.json"
SIGNAL_LOG = "signals.json"

def load_trades():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG) as f:
            return json.load(f)
    return []

def load_signals():
    if os.path.exists(SIGNAL_LOG):
        with open(SIGNAL_LOG) as f:
            return json.load(f)
    return []

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/account")
def api_account():
    try:
        account = get_account()
        clock = trading_client.get_clock()
        return jsonify({
            "equity": str(account.equity),
            "buying_power": str(account.buying_power),
            "cash": str(account.cash),
            "market_open": clock.is_open
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/positions")
def api_positions():
    try:
        positions = get_positions()
        return jsonify([{
            "symbol": p.symbol,
            "qty": str(p.qty),
            "avg_entry_price": str(p.avg_entry_price),
            "current_price": str(p.current_price),
            "unrealized_pl": str(p.unrealized_pl),
            "unrealized_plpc": str(p.unrealized_plpc)
        } for p in positions])
    except Exception as e:
        return jsonify([])

@app.route("/api/trades")
def api_trades():
    return jsonify(load_trades())

@app.route("/api/signals")
def api_signals():
    return jsonify(load_signals())

@app.route("/api/benchmarks")
def api_benchmarks():
    metrics = calculate_metrics()
    tier_info = get_current_tier(metrics)
    return jsonify({**metrics, **tier_info})

if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\n🚀 Dashboard running at:")
    print(f"   Computer : http://localhost:5001")
    print(f"   Phone    : http://{local_ip}:5001")
    print(f"\n   Open either in your browser\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
