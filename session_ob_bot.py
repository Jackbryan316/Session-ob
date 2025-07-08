import os
import time
import requests
import datetime
from flask import Flask, jsonify
from threading import Thread

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", 0))  # in hours

PAIRS = ["XAU_USD", "GBP_USD", "EUR_USD", "USD_JPY", "GBP_JPY"]
TIMEFRAME = "H4"  # ✅ This is now fixed back to 4-hour timeframe

app = Flask(__name__)

def is_market_open():
    now = datetime.datetime.utcnow()
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    return True

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

def detect_order_block(candles):
    if len(candles) < 3:
        return None

    c1 = candles[-3]
    c2 = candles[-2]
    c3 = candles[-1]

    def is_bullish(c): return float(c["mid"]["c"]) > float(c["mid"]["o"])
    def is_bearish(c): return float(c["mid"]["c"]) < float(c["mid"]["o"])

    if is_bearish(c1) and is_bullish(c2) and is_bullish(c3):
        return {
            "type": "Bullish OB",
            "entry": c2["mid"]["o"],
            "exit": c3["mid"]["c"]
        }
    elif is_bullish(c1) and is_bearish(c2) and is_bearish(c3):
        return {
            "type": "Bearish OB",
            "entry": c2["mid"]["o"],
            "exit": c3["mid"]["c"]
        }
    return None

def send_discord_alert(pair, ob_type, entry, exit):
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE_OFFSET)
    chart_link = f"https://www.tradingview.com/chart/?symbol=OANDA:{pair}"
    embed = {
        "title": f"{ob_type} Detected on {pair}",
        "description": f"📍 **Entry**: `{entry}`\n🎯 **Exit**: `{exit}`\n\n[📈 View on TradingView]({chart_link})",
        "color": 65280 if "Bullish" in ob_type else 16711680,
        "timestamp": now.isoformat()
    }
    data = {
        "embeds": [embed]
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print(f"✅ Alert sent for {pair}")
    else:
        print(f"❌ Failed to send alert: {response.status_code} - {response.text}")

def scan_market():
    while True:
        if not is_market_open():
            print("📴 Market is closed. No scan.")
            time.sleep(300)
            continue

        print("🔄 Scanning for OB setups...")
        for pair in PAIRS:
            print(f"🔍 Checking {pair}...")
            candles = fetch_candles(pair)
            ob = detect_order_block(candles)
            if ob:
                send_discord_alert(pair, ob["type"], ob["entry"], ob["exit"])
            else:
                print(f"No valid OB setup on {pair}")

        print("⏱️ Waiting 5 mins...")
        time.sleep(300)

@app.route('/')
def home():
    return jsonify({"status": "Session OB Bot is running"})

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    scan_market()











