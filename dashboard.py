from flask import Flask, jsonify, render_template_string
import datetime

app = Flask(__name__)

# Sample status data
bot_status = {
    "VWAP_Liquidity_Bot": {
        "status": "Running",
        "last_checked": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "pairs": ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY", "GBPJPY"],
        "timeframe": "H4 + M15",
        "last_signal": "No setup"
    },
    "Session_OB_Bot": {
        "status": "Running",
        "last_checked": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "pairs": ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY", "GBPJPY"],
        "timeframe": "H1 + M15",
        "last_signal": "No setup"
    }
}

template = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot Dashboard</title>
    <style>
        body { font-family: Arial; background: #111; color: #eee; padding: 20px; }
        h1 { color: #00ffcc; }
        .bot-card { background: #222; padding: 20px; margin-bottom: 15px; border-radius: 10px; }
        .bot-card h2 { color: #00c3ff; }
    </style>
</head>
<body>
    <h1>📊 Trading Bot Dashboard</h1>
    {% for bot, info in bots.items() %}
    <div class="bot-card">
        <h2>{{ bot.replace("_", " ") }}</h2>
        <p>Status: <b>{{ info.status }}</b></p>
        <p>Last Checked: {{ info.last_checked }}</p>
        <p>Timeframe: {{ info.timeframe }}</p>
        <p>Pairs Monitored: {{ info.pairs | join(', ') }}</p>
        <p>Last Signal: <b>{{ info.last_signal }}</b></p>
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(template, bots=bot_status)

@app.route("/api/status")
def api_status():
    return jsonify(bot_status)

app.run(host="0.0.0.0", port=7860)
