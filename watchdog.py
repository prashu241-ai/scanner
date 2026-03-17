import subprocess

CHAT_ID = "5186511939"

def send(msg):
    subprocess.run([
        "openclaw", "message", "send",
        "--channel", "telegram",
        "--target", CHAT_ID,
        "--message", msg
    ])

def is_running():
    result = subprocess.run(
        ["pgrep", "-f", "breakout_scanner.py"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip() != ""

if not is_running():
    send("🚨 Scanner STOPPED! Restarting now...")
    subprocess.run(["systemctl", "restart", "scanner"])
