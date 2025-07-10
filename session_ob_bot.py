
# Session OB Bot with Dynamic RR (1:2) and Liquidity Sweep + Rejection

import os
import time
import requests
import datetime
from flask import Flask, jsonify
from threading import Thread

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", 0))

PAIRS = ["XAU_USD", "GBP_USD", "EUR_USD"]
TIMEFRAME = "H4"

app = Flask(__name__)
last_alerts = {}

def is_market_open():
    now = datetime.datetime.utcnow()
    return now.weekday() < 5

def fetch_candles(pair):
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{pair}/candles"
    params = {"count": 15, "granularity": TIMEFRAME, "price": "M"}
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Error fetching {pair}: {response.status_code}")
        return []
    return response.json().get("candles", [])

def detect_ob_with_liquidity_sweep(candles):
    if len(candles) < 10:
        return None

    highs = [float(c["mid"]["h"]) for c in candles[-10:]]
    lows = [float(c["mid"]["l"]) for c in candles[-10:]]

    recent = candles[-1]
    prev = candles[-2]
    recent_high = float(recent["mid"]["h"])
    recent_low = float(recent["mid"]["l"])
    recent_close = float(recent["mid"]["c"])
    prev_high = float(prev["mid"]["h"])
    prev_low = float(prev["mid"]["l"])

    max_high = max(highs[:-2])
    min_low = min(lows[:-2])
    rr_ratio = 2  # Risk:Reward = 1:2

    # Bullish OB
    if recent_low < min_low and recent_close > prev_high:
        sl = recent_low
        sl_distance = recent_close - sl
        tp = recent_close + (sl_distance * rr_ratio)
        return {
            "type": "Bullish OB",
            "entry": round(recent_close, 5),
            "exit": round(tp, 5),
            "sl": round(sl, 5)
        }

    # Bearish OB
    elif recent_high > max_high and recent_close < prev_low:
        sl = recent_high
        sl_distance = sl - recent_close
        tp = recent_close - (sl_distance * rr_ratio)
        return {
            "type": "Bearish OB",
            "entry": round(recent_close, 5),
            "exit": round(tp, 5),
            "sl": round(sl, 5)
        }

    return None

def send_discord_alert(pair, ob):
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE_OFFSET)
    chart_link = f"https://www.tradingview.com/chart/?symbol=OANDA:{pair.replace('_', '')}"
    embed = {
        "title": f"{ob['type']} Detected on {pair}",
        "description": (
            f"📍 **Entry**: `{ob['entry']}`\n"
            f"🎯 **TP**: `{ob['exit']}`\n"
            f"🛑 **SL**: `{ob['sl']}`\n\n"
            f"[📈 View on TradingView]({chart_link})"
        ),
        "color": 65280 if "Bullish" in ob["type"] else 16711680,
        "timestamp": now.isoformat()
    }
    data = {"embeds": [embed]}
    res = requests.post(DISCORD_WEBHOOK_URL, json=data)
    print("✅ Alert sent" if res.status_code == 204 else f"❌ Failed: {res.text}")

def scan_market():
    while True:
        if not is_market_open():
            print("📴 Market is closed.")
            time.sleep(300)
            continue

        print("🔎 Scanning...")
        for pair in PAIRS:
            candles = fetch_candles(pair)
            ob = detect_ob_with_liquidity_sweep(candles)
            if ob:
                last = last_alerts.get(pair)
                if last != ob["entry"]:
                    send_discord_alert(pair, ob)
                    last_alerts[pair] = ob["entry"]
                else:
                    print(f"⚠️ Duplicate alert skipped for {pair}")
            else:
                print(f"No OB on {pair}")
        time.sleep(300)

@app.route('/')
def home():
    return jsonify({"status": "Session OB Bot running"})

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    scan_market()


















