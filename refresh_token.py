import os
import json
import requests
from kiteconnect import KiteConnect
from datetime import datetime

# ── Config ──────────────────────────────────────────
KITE_API_KEY      = "3wbhan16xjugru90"
KITE_API_SECRET   = "5zxg87zeoe9hennhfhnu7wp0la5p73tr"
TELEGRAM_CHAT_ID  = "5186511939"
OPENCLAW_TOKEN    = "7e3965a24a2c5200ce4e15fc5bafef243dca553f6aa50a86"
OPENCLAW_WEBHOOK  = "http://localhost:18789/webhook"
TOKEN_FILE        = "/home/prashu/stocks/access_token.json"

kite = KiteConnect(api_key=KITE_API_KEY)

# ── Save token to file ───────────────────────────────
def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": token,
            "date": datetime.now().strftime("%Y-%m-%d")
        }, f)
    print(f"[TOKEN SAVED] {token}")

# ── Load token from file ─────────────────────────────
def load_token():
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if data.get("date") == today:
                return data.get("access_token")
    except:
        pass
    return None

# ── Send Telegram message ────────────────────────────
def send_telegram(msg):
    try:
        requests.post(
            OPENCLAW_WEBHOOK,
            headers={"Authorization": f"Bearer {OPENCLAW_TOKEN}"},
            json={
                "message": msg,
                "target": TELEGRAM_CHAT_ID,
                "channel": "telegram"
            },
            timeout=5
        )
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")

# ── Send login link to Telegram ──────────────────────
def send_login_link():
    login_url = kite.login_url()
    msg = (
        f"🔐 *Zerodha Token Refresh Required*\n\n"
        f"Click the link below to login and get today's token:\n"
        f"{login_url}\n\n"
        f"After login, copy the `request_token` from the redirect URL and reply:\n"
        f"`/token YOUR_REQUEST_TOKEN`"
    )
    send_telegram(msg)
    print("[LOGIN LINK SENT] Check Telegram")

# ── Main ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Called with request_token as argument
        request_token = sys.argv[1]
        try:
            data = kite.generate_session(
                request_token,
                api_secret=KITE_API_SECRET
            )
            access_token = data["access_token"]
            save_token(access_token)

            # Update breakout scanner config
            scanner = "/home/prashu/stocks/breakout_scanner.py"
            with open(scanner, "r") as f:
                content = f.read()

            # Replace old token
            import re
            content = re.sub(
                r'KITE_ACCESS_TOKEN\s*=\s*".*?"',
                f'KITE_ACCESS_TOKEN = "{access_token}"',
                content
            )
            with open(scanner, "w") as f:
                f.write(content)

            send_telegram(
                f"✅ *Token refreshed successfully!*\n"
                f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"🤖 Stock scanner restarting..."
            )

            # Restart stock scanner service
            os.system("sudo systemctl restart stock-scanner")
            print("[SUCCESS] Token updated and scanner restarted!")

        except Exception as e:
            send_telegram(f"❌ Token refresh failed: {str(e)}")
            print(f"[ERROR] {e}")
    else:
        # No argument — just send login link
        send_login_link()
