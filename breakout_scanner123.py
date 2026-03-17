import time
import requests
from kiteconnect import KiteConnect
from datetime import datetime

# ── Config ──────────────────────────────────────────
KITE_API_KEY    = "3wbhan16xjugru90"
KITE_API_SECRET = "5zxg87zeoe9hennhfhnu7wp0la5p73tr"
KITE_ACCESS_TOKEN = "lRUsHOZRjXjPUX2vZzdTt2z6iYptwxg6"
TELEGRAM_CHAT_ID = "5186511939"

# Your watchlist of stocks
WATCHLIST = [
    "NSE:RELIANCE",
    "NSE:TCS",
    "NSE:INFY",
    "NSE:HDFCBANK",
    "NSE:ICICIBANK",
    "NSE:BAJFINANCE",
    "NSE:LT",
    "NSE:BHARTIARTL",
    "NSE:SBIN",
    "NSE:ETERNAL",
]

# Breakout config
BREAKOUT_PERIOD = 20        # 20-candle high/low breakout
CANDLE_INTERVAL = "5minute"
ALERT_COOLDOWN  = 300       # seconds between alerts for same stock

# OpenClaw webhook (we'll set this up next)
OPENCLAW_WEBHOOK_URL = "http://localhost:18789/webhook"
OPENCLAW_TOKEN       = "7e3965a24a2c5200ce4e15fc5bafef243dca553f6aa50a86"

# ── State ────────────────────────────────────────────
last_alert = {}

# ── Kite Setup ───────────────────────────────────────
kite = KiteConnect(api_key=KITE_API_KEY)
kite.set_access_token(KITE_ACCESS_TOKEN)

# ── Send Telegram via OpenClaw ───────────────────────
def send_telegram_alert(symbol, signal, price, high, low):
    emoji = "🟢" if signal == "BUY" else "🔴"
    msg = (
        f"{emoji} *{signal} SIGNAL — {symbol}*\n"
        f"📈 Price: ₹{price}\n"
        f"🔺 {BREAKOUT_PERIOD}-bar High: ₹{high}\n"
        f"🔻 {BREAKOUT_PERIOD}-bar Low: ₹{low}\n"
        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n"
        f"📊 Strategy: Price Breakout"
    )
    try:
        requests.post(
            f"{OPENCLAW_WEBHOOK_URL}",
            headers={"Authorization": f"Bearer {OPENCLAW_TOKEN}"},
            json={
                "message": msg,
                "target": TELEGRAM_CHAT_ID,
                "channel": "telegram"
            },
            timeout=5
        )
        print(f"[ALERT SENT] {signal} {symbol} @ ₹{price}")
    except Exception as e:
        print(f"[ERROR] Failed to send alert: {e}")

# ── Breakout Detection ───────────────────────────────
def check_breakout(symbol):
    try:
        instrument = kite.ltp([symbol])
        current_price = instrument[symbol]["last_price"]

        # Get historical candles
        from_date = datetime.now().replace(hour=9, minute=15, second=0)
        to_date   = datetime.now()
        candles   = kite.historical_data(
            instrument_token=instrument[symbol]["instrument_token"],
            from_date=from_date,
            to_date=to_date,
            interval=CANDLE_INTERVAL
        )

        if len(candles) < BREAKOUT_PERIOD:
            return

        highs = [c["high"] for c in candles[-BREAKOUT_PERIOD:]]
        lows  = [c["low"]  for c in candles[-BREAKOUT_PERIOD:]]
        period_high = max(highs)
        period_low  = min(lows)

        now = time.time()
        cooldown_ok = (now - last_alert.get(symbol, 0)) > ALERT_COOLDOWN

        if current_price > period_high and cooldown_ok:
            last_alert[symbol] = now
            send_telegram_alert(symbol, "BUY", current_price, period_high, period_low)

        elif current_price < period_low and cooldown_ok:
            last_alert[symbol] = now
            send_telegram_alert(symbol, "SELL", current_price, period_high, period_low)

    except Exception as e:
        print(f"[ERROR] {symbol}: {e}")

# ── Main Loop ────────────────────────────────────────
def main():
    print("🦞 OpenClaw Stock Scanner Started")
    print(f"Watching: {', '.join(WATCHLIST)}")
    print(f"Strategy: {BREAKOUT_PERIOD}-bar Price Breakout\n")

    while True:
        now = datetime.now()
        # Only run during market hours (9:15 AM - 3:30 PM IST)
        if now.weekday() < 5 and \
           (9*60+15) <= (now.hour*60 + now.minute) <= (15*60+30):
            print(f"[{now.strftime('%H:%M:%S')}] Scanning {len(WATCHLIST)} stocks...")
            for symbol in WATCHLIST:
                check_breakout(symbol)
                time.sleep(1)  # avoid rate limits
        else:
            print(f"[{now.strftime('%H:%M:%S')}] Market closed. Waiting...")

        time.sleep(60)  # scan every minute

if __name__ == "__main__":
    main()
