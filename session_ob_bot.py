import os
import time
import requests
import datetime
from flask import Flask, jsonify
from threading import Thread

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", 0))

PAIRS = ["XAU_USD", "GBP_USD", "EUR_USD", "USD_JPY", "GBP_JPY"]
TIMEFRAME = "H4"

app = Flask(__name__)

def is_market_open():
    now = datetime.datetime.utcnow()
    return now.weekday() < 5

def fetch_candles(pair):
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{pair}/candles"
    params = {
        "count": 10,
        "granularity": TIMEFRAME,
        "price": "M"
    }
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Failed to fetch candles for {pair}: {response.status_code}")
        return []
    return response.json().get("candles", [])

def detect_liquidity_sweep_rejection(candles):
    if len(candles) < 4:
        return None

    c1 = candles[-4]
    c2 = candles[-3]
    c3 = candles[-2]
    c4 = candles[-1]

    def to_float(c): return float(c["mid"]["c"]), float(c["mid"]["o"]), float(c["mid"]["h"]), float(c["mid"]["l"])
    c3_close, c3_open, c3_high, c3_low = to_float(c3)
    c4_close, c4_open, c4_high, c4_low = to_float(c4)

    # Sweep: candle 3 sweeps high or low, then rejection from candle 4
    if c3_high > max(float(c["mid"]["h"]) for c in candles[-6:-3]) and c4_close < c4_open:
        return {"type": "Bearish OB", "entry": c4_open, "exit": c4_close}
    elif c3_low < min(float(c["mid"]["l"]) for c in candles[-6:-3]) and c4_close > c4_open:
        return {"type": "Bullish OB", "entry": c4_open, "exit": c4_close}
    return None

def send_discord_alert(pair, ob_type, entry, exit):
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE_OFFSET)
    chart_symbol = pair.replace("_", "")
    chart_link = f"https://www.tradingview.com/chart/?symbol=FX:{chart_symbol}"
    embed = {
        "title": f"{ob_type} Detected on {pair}",
        "description": f"📍 **Entry**: `{entry}`\n🎯 **Exit**: `{exit}`\n\n[📈 View on TradingView]({chart_link})",
        "color": 65280 if "Bullish" in ob_type else 16711680,
        "timestamp": now.isoformat()
    }
    data = {"embeds": [embed]}
    res = requests.post(DISCORD_WEBHOOK_URL, json=data)
    print("✅ Alert sent" if res.status_code == 204 else f"❌ Alert failed: {res.status_code} - {res.text}")

def scan_market():
    while True:
        if not is_market_open():
            print("📴 Market is closed. Skipping scan.")
            time.sleep(300)
            continue

        print("🔄 Scanning H4 chart...")
        for pair in PAIRS:
            candles = fetch_candles(pair)
            if not candles:
                continue
            ob = detect_liquidity_sweep_rejection(candles)
            if ob:
                send_discord_alert(pair, ob["type"], ob["entry"], ob["exit"])
            else:
                print(f"No valid setup on {pair}")
        print("⏳ Sleeping 5 mins...\n")
        time.sleep(300)

@app.route('/')
def home():
    return jsonify({"status": "Session OB Bot is running"})

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    scan_market()



















