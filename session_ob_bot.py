
import os import time import requests import datetime from flask import Flask, jsonify from threading import Thread

=============== CONFIG ===============

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "") OANDA_API_KEY = os.getenv("OANDA_API_KEY", "") TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", "1"))  # Nigeria is UTC+1 PAIR_LIST = ["XAU_USD", "GBP_USD", "EUR_USD", "USD_JPY", "GBP_JPY"] LOG_FILE = "logs.txt"

=============== FLASK DASHBOARD ===============

app = Flask(name) status = {"last_checked": None, "last_signal": None}

@app.route("/status") def get_status(): return jsonify(status)

def run_flask(): app.run(host="0.0.0.0", port=7860)

=============== LOGGING ===============

def log_event(message): timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") with open(LOG_FILE, "a") as f: f.write(f"[{timestamp}] {message}\n") print(message)

=============== CANDLE FETCH ===============

def fetch_candles(pair): url = f"https://api-fxpractice.oanda.com/v3/instruments/{pair}/candles" headers = {"Authorization": f"Bearer {OANDA_API_KEY}"} params = {"granularity": "H4", "count": 5} response = requests.get(url, headers=headers, params=params) if response.status_code == 200: candles = response.json()["candles"] return [candle for candle in candles if candle["complete"]] else: log_event(f"❌ Error fetching candles for {pair}: {response.text}") return []

=============== ENGULFING OB DETECTION ===============

def detect_ob(pair): candles = fetch_candles(pair) if len(candles) < 2: return None

prev = candles[-2]["mid"]
curr = candles[-1]["mid"]

prev_body = float(prev["c"]) - float(prev["o"])
curr_body = float(curr["c"]) - float(curr["o"])

# Bearish Engulfing
if prev_body > 0 and curr_body < 0 and float(curr["o"]) > float(prev["c"]) and float(curr["c"]) < float(prev["o"]):
    return {"type": "bearish", "entry": curr["c"], "exit": float(curr["c"]) - 50}
# Bullish Engulfing
elif prev_body < 0 and curr_body > 0 and float(curr["o"]) < float(prev["c"]) and float(curr["c"]) > float(prev["o"]):
    return {"type": "bullish", "entry": curr["c"], "exit": float(curr["c"]) + 50}
return None

=============== ALERT SENDER ===============

def send_alert(pair, signal_type, entry, exit): chart_url = f"https://www.tradingview.com/chart/?symbol=OANDA:{pair.replace('_', '')}" content = f"📌 {signal_type.upper()} OB Signal on {pair}\n\nEntry: {entry}\nExit: {exit}\n\n📈 View Chart" data = {"content": content}

try:
    res = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if res.status_code == 204:
        log_event(f"✅ Alert sent for {pair}")
        status["last_signal"] = f"{pair} - {signal_type}"
    else:
        log_event(f"❌ Failed to send alert for {pair}: {res.text}")
except Exception as e:
    log_event(f"❌ Exception sending alert: {e}")

=============== MAIN LOOP ===============

def run_bot(): while True: now = datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE_OFFSET) weekday = now.weekday() hour = now.hour minute = now.minute

if weekday == 6 or (weekday == 0 and hour < 22):
        log_event("📴 Market is closed. No scan.")
        time.sleep(300)
        continue

    log_event("🔍 Starting OB scan...")
    for pair in PAIR_LIST:
        log_event(f"🔎 Checking {pair}...")
        result = detect_ob(pair)
        if result:
            send_alert(pair, result["type"], result["entry"], result["exit"])
        else:
            log_event(f"No OB setup on {pair}")

    status["last_checked"] = now.strftime("%Y-%m-%d %H:%M:%S")
    time.sleep(300)  # Wait 5 minutes

=============== RUN EVERYTHING ===============

Thread(target=run_flask).start() run_bot()

