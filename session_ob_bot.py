import os
import time
import requests
import datetime
from flask import Flask, jsonify
from threading import Thread

# === CONFIGURATION ===
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", 1))  # Default is GMT+1
PAIRS = ["XAU_USD", "GBP_USD", "EUR_USD", "USD_JPY", "GBP_JPY"]
TIMEFRAME = "H4"

# === LOGGING ===
def log(message):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs.txt", "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

# === HELPER FUNCTIONS ===
def is_market_open():
    now_utc = datetime.datetime.utcnow()
    local_time = now_utc + datetime.timedelta(hours=TIMEZONE_OFFSET)
    if local_time.weekday() == 6:  # Sunday
        if local_time.hour < 22:
            return False
    elif local_time.weekday() == 5:  # Saturday
        return False
    return True

def fetch_candles(pair, count=5):
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{pair}/candles"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {
        "granularity": TIMEFRAME,
        "count": count,
        "price": "M"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        candles = data.get("candles", [])
        return [
            {
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"]),
                "time": c["time"]
            }
            for c in candles if c["complete"]
        ]
    except Exception as e:
        log(f"❌ Error fetching candles for {pair}: {e}")
        return []

def detect_bullish_engulfing(prev, current):
    return prev["close"] < prev["open"] and current["close"] > current["open"] and current["close"] > prev["open"] and current["open"] < prev["close"]

def detect_bearish_engulfing(prev, current):
    return prev["close"] > prev["open"] and current["close"] < current["open"] and current["close"] < prev["open"] and current["open"] > prev["close"]

def analyze_pair(pair):
    log(f"🔍 Scanning {pair} for OB setup...")
    candles = fetch_candles(pair)
    if len(candles) < 2:
        log(f"⚠️ Not enough data for {pair}")
        return

    prev, current = candles[-2], candles[-1]
    entry_price = current["close"]
    sl = current["low"] if current["close"] > current["open"] else current["high"]
    tp = round(entry_price + (entry_price - sl) * 2, 3) if current["close"] > current["open"] else round(entry_price - (sl - entry_price) * 2, 3)

    if detect_bullish_engulfing(prev, current):
        message = (
            f"📈 **Bullish OB detected** on {pair}\n"
            f"🕒 Time: {current['time']}\n"
            f"📥 Entry: {entry_price}\n"
            f"⛔ SL: {sl}\n"
            f"🎯 TP: {tp}\n"
            f"[📷 View Chart](https://www.tradingview.com/chart/)\n"
        )
        send_discord_alert(message)
    elif detect_bearish_engulfing(prev, current):
        message = (
            f"📉 **Bearish OB detected** on {pair}\n"
            f"🕒 Time: {current['time']}\n"
            f"📥 Entry: {entry_price}\n"
            f"⛔ SL: {sl}\n"
            f"🎯 TP: {tp}\n"
            f"[📷 View Chart](https://www.tradingview.com/chart/)\n"
        )
        send_discord_alert(message)
    else:
        log(f"No setup on {pair}")

def send_discord_alert(message):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        log(f"✅ Signal sent")
    except Exception as e:
        log(f"❌ Error sending signal: {e}")

# === MAIN SCANNER LOOP ===
def run_bot():
    while True:
        if not is_market_open():
            log("📴 Market is closed. No scan.")
            time.sleep(300)
            continue

        now = datetime.datetime.utcnow()
        if now.minute % 15 != 0:
            log("⏳ Waiting for 15-minute mark...")
            time.sleep(60)
            continue

        for pair in PAIRS:
            analyze_pair(pair)

        time.sleep(300)

# === DASHBOARD ===
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "Bot is running", "last_updated": datetime.datetime.utcnow().isoformat()})

def start_dashboard():
    app.run(host="0.0.0.0", port=10000)

if __name__ == '__main__':
    Thread(target=start_dashboard).start()
    run_bot()
