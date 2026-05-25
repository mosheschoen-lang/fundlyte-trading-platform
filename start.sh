#!/bin/bash
# Start both the trading engine and dashboard together

cd "$(dirname "$0")"

echo "🚀 Starting FundLyte Trading Platform..."
echo ""

# Start dashboard in background
python3 dashboard.py &
DASHBOARD_PID=$!

echo "📊 Dashboard started (PID $DASHBOARD_PID)"
echo ""
echo "   Open in browser: http://localhost:5001"
echo "   Open on phone:   same WiFi, use your Mac's IP:5001"
echo ""
echo "⚡ Starting trading engine..."
echo ""

# Start trading engine (foreground)
python3 engine.py

# If engine stops, kill dashboard too
kill $DASHBOARD_PID
