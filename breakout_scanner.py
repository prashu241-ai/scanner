#!/usr/bin/env python3

import time
import subprocess
from datetime import datetime
import pytz
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

IST = pytz.timezone("Asia/Kolkata")

# ───────────────── CONFIG ─────────────────

TELEGRAM_CHAT_ID = "5186511939"

SCAN_INTERVAL = 300
ALERT_COOLDOWN = 300

BREAKOUT_PERIOD = 20
RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

SUPERTREND_PERIOD = 10
SUPERTREND_MULT = 3

VOLUME_SURGE = 1.5


# ───────────────── LTP WATCHLIST ─────────────────

LTP_WATCHLIST = [
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

LTP_YF = [s.replace("NSE:", "") + ".NS" for s in LTP_WATCHLIST]


# ───────────────── MAIN WATCHLIST ─────────────────

WATCHLIST = [
"RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
"HINDUNILVR.NS","ITC.NS","KOTAKBANK.NS","LT.NS","SBIN.NS",
"AXISBANK.NS","BHARTIARTL.NS","BAJFINANCE.NS","MARUTI.NS","WIPRO.NS",
"HCLTECH.NS","ASIANPAINT.NS","SUNPHARMA.NS","ULTRACEMCO.NS","TITAN.NS",
"BAJAJFINSV.NS","NESTLEIND.NS","POWERGRID.NS","NTPC.NS","TECHM.NS",
"TATAMOTORS.NS","TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","ONGC.NS",
"COALINDIA.NS","BPCL.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS",
"EICHERMOT.NS","HEROMOTOCO.NS","BAJAJ-AUTO.NS","BRITANNIA.NS","GRASIM.NS",
"ADANIENT.NS","ADANIPORTS.NS","INDUSINDBK.NS","M&M.NS","TATACONSUM.NS",
"APOLLOHOSP.NS","LTIMINDTREE.NS","HDFCLIFE.NS","SBILIFE.NS","SHRIRAMFIN.NS",
]


# ───────────────── STATE ─────────────────

last_alert = {}
signals_today = []
ltp_sent = False
eod_sent = False


# ───────────────── TELEGRAM ─────────────────

def send_telegram(msg):

    try:

        subprocess.run(
            [
                "openclaw",
                "message",
                "send",
                "--channel",
                "telegram",
                "--target",
                TELEGRAM_CHAT_ID,
                "--message",
                msg,
            ],
            capture_output=True,
            text=True,
        )

    except Exception as e:

        print("Telegram error:", e)


# ───────────────── INDICATORS ─────────────────

def calc_rsi(series):

    delta = series.diff()

    gain = delta.clip(lower=0).rolling(RSI_PERIOD).mean()

    loss = (-delta.clip(upper=0)).rolling(RSI_PERIOD).mean()

    rs = gain / loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def calc_macd(series):

    ema_fast = series.ewm(span=MACD_FAST, adjust=False).mean()

    ema_slow = series.ewm(span=MACD_SLOW, adjust=False).mean()

    macd = ema_fast - ema_slow

    signal = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()

    hist = macd - signal

    return macd, signal, hist


def calc_supertrend(df):

    high = df["High"]

    low = df["Low"]

    close = df["Close"]

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(SUPERTREND_PERIOD).mean()

    hl2 = (high + low) / 2

    upper = hl2 + SUPERTREND_MULT * atr

    lower = hl2 - SUPERTREND_MULT * atr

    direction = pd.Series(index=close.index, dtype=float)

    direction.iloc[0] = 1

    for i in range(1, len(close)):

        if close.iloc[i] > upper.iloc[i - 1]:

            direction.iloc[i] = 1

        elif close.iloc[i] < lower.iloc[i - 1]:

            direction.iloc[i] = -1

        else:

            direction.iloc[i] = direction.iloc[i - 1]

    return direction


# ───────────────── SIGNAL LOGIC ─────────────────

def calc_all_signals(df):

    if df is None or len(df) < 50:

        return None

    close = df["Close"]

    high = df["High"]

    low = df["Low"]

    volume = df["Volume"]

    price = float(close.iloc[-1])

    prev_close = float(close.iloc[-2])

    change_pct = ((price - prev_close) / prev_close) * 100

    period_high = high.tail(BREAKOUT_PERIOD + 1).iloc[:-1].max()

    period_low = low.tail(BREAKOUT_PERIOD + 1).iloc[:-1].min()

    breakout_buy = price > period_high

    breakout_sell = price < period_low

    rsi = calc_rsi(close)

    rsi_now = float(rsi.iloc[-1])

    rsi_buy = rsi_now < RSI_OVERSOLD

    rsi_sell = rsi_now > RSI_OVERBOUGHT

    macd, signal, hist = calc_macd(close)

    if len(macd) < 2:

        return None

    macd_cross_up = macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]

    macd_cross_down = macd.iloc[-2] > signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]

    st = calc_supertrend(df)

    if pd.isna(st.iloc[-1]) or pd.isna(st.iloc[-2]):

        return None

    st_now = int(st.iloc[-1])

    st_prev = int(st.iloc[-2])

    st_flip_up = st_prev == -1 and st_now == 1

    st_flip_down = st_prev == 1 and st_now == -1

    avg_vol = volume.iloc[-20:-1].mean()

    curr_vol = volume.iloc[-1]

    vol_surge = curr_vol > avg_vol * VOLUME_SURGE if avg_vol else False

    buy_score = sum([breakout_buy, rsi_buy, macd_cross_up, st_flip_up, vol_surge])

    sell_score = sum([breakout_sell, rsi_sell, macd_cross_down, st_flip_down, vol_surge])

    return {

        "price": round(price, 2),

        "change_pct": round(change_pct, 2),

        "buy_score": buy_score,

        "sell_score": sell_score,

    }


# ───────────────── LTP REPORT ─────────────────

def send_ltp_report():

    print("Fetching LTP...")

    data = yf.download(

        tickers=LTP_YF,

        period="2d",

        interval="1d",

        progress=False,

        threads=True,

    )

    lines = [

        "📊 Last Traded Prices",

        datetime.now(IST).strftime("%d %b %Y %H:%M"),

        "────────────",

    ]

    for nse, yf_sym in zip(LTP_WATCHLIST, LTP_YF):

        try:

            closes = data["Close"][yf_sym].dropna()

            if len(closes) < 2:

                continue

            ltp = float(closes.iloc[-1])

            prev = float(closes.iloc[-2])

            chg = ((ltp - prev) / prev) * 100

            arrow = "🟢" if chg >= 0 else "🔴"

            name = nse.replace("NSE:", "")

            lines.append(f"{arrow} {name} ₹{ltp:.2f} ({chg:+.2f}%)")

        except:

            pass

    send_telegram("\n".join(lines))


# ───────────────── MARKET HOURS ─────────────────

def is_market_open():

    now = datetime.now(IST)

    if now.weekday() >= 5:

        return False

    minutes = now.hour * 60 + now.minute

    return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)


# ───────────────── MAIN LOOP ─────────────────

def main():

    global ltp_sent

    print("⚡ AlgoScanner Started")

    send_telegram("⚡ AlgoScanner Started")

    while True:

        now = datetime.now(IST)

        if is_market_open():

            print("Market Open")

            time.sleep(SCAN_INTERVAL)

        else:

            if not ltp_sent:

                print("Market Closed → Sending LTP")

                send_ltp_report()

                ltp_sent = True

            print("Market Closed")

            time.sleep(300)


if __name__ == "__main__":
while True:
    now = datetime.now(IST)

    if is_market_open():
        print("Market Open → Scanning")
        ltp_sent = False   # reset for next day
        scan_market()      # your scanning function
        time.sleep(SCAN_INTERVAL)

    else:
        if not ltp_sent:
            print("Market Closed → Sending LTP")
            send_ltp_report()
            ltp_sent = True

        print("Market Closed")
        time.sleep(300)

    main()
