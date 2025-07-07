import requests
import datetime
import pytz

# Discord webhook
WEBHOOK_URL = "https://discord.com/api/webhooks/1391664965026447401/eLaXj078VSscwc8FnR4rckBBfIzgwH7DPkAl_uy3yBDVabq-wGmqP_fUJ_EI2NCu2yez"

# Logging file
LOG_FILE = "session_ob_logs.txt"

# Mock OB scanner (replace with real OB detection logic later)
def detect_order_block(pair, price):
    # Simulate OB detection based on odd/even minute
    now = datetime.datetime.utcnow()
    if now.minute % 2 == 0:
        return "Bullish"
    elif now.minute % 3 == 0:
        return "Bearish"
    return None

# Market open check (Mon 10PM to Fri 10PM GMT)
def is_market_open():
    now = datetime.datetime.now(pytz.timezone("Africa/Lagos"))
    weekday = now.weekday()
    hour = now.hour
    if weekday == 6 or (weekday == 0 and hour < 22):
        return False
    return True

# Send alert to Discord
def send_discord_alert(pair, direction, entry, sl, tp):
    timestamp = datetime.datetime.now(pytz.timezone("Africa/Lagos")).strftime("%Y-%m-%d %H:%M:%S")
    content = (
        f"📈 **{direction} Order Block Detected** on `{pair}`\n"
        f"🕒 {timestamp}\n"
        f"💰 Entry: `{entry}`\n"
        f"🛑 SL: `{sl}` | 🎯 TP: `{tp}`"
    )
    requests.post(WEBHOOK_URL, json={"content": content})

    # Save to log file
    with open(LOG_FILE, "a") as log:
        log.write(f"{timestamp} - {pair} - {direction} OB\n")
        log.write(f"Entry: {entry} | SL: {sl} | TP: {tp}\n\n")

# Main bot logic
def run_bot():
    if not is_market_open():
        print("📴 Market is closed. No scan.")
        return

    print("🔍 Scanning for OB setups...\n")
    pairs = ["XAU_USD", "GBP_USD", "EUR_USD", "USD_JPY", "GBP_JPY"]
    current_price = {
        "XAU_USD": 2365.00,
        "GBP_USD": 1.2820,
        "EUR_USD": 1.0852,
        "USD_JPY": 161.30,
        "GBP_JPY": 206.15
    }

    for pair in pairs:
        print(f"🔍 Scanning {pair}...")
        direction = detect_order_block(pair, current_price[pair])
        if direction:
            entry = current_price[pair]
            sl = round(entry - 0.0010, 4) if direction == "Bullish" else round(entry + 0.0010, 4)
            tp = round(entry + 0.0030, 4) if direction == "Bullish" else round(entry - 0.0030, 4)

            send_discord_alert(pair, direction, entry, sl, tp)
            print(f"✅ Signal sent for {pair} ({direction})\n")
        else:
            print(f"❌ No OB setup on {pair}\n")

# Run bot
run_bot()
