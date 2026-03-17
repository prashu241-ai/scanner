#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║     ⚡ OpenClaw NSE AlgoScanner — Complete Edition           ║
║     Strategies : Breakout + RSI + MACD + Supertrend         ║
║     Data       : yfinance (batch, 15-20x faster)            ║
║     Alerts     : Telegram via OpenClaw CLI                  ║
║     Author     : Prakhar Goel                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import time
import subprocess
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════
#  CONFIG — edit these values
# ═══════════════════════════════════════════════════════════════

TELEGRAM_CHAT_ID  = "5186511939"
SCAN_INTERVAL     = 60           # seconds between scans during market hours
ALERT_COOLDOWN    = 300          # seconds between repeat alerts for same stock

# ── Strategy Parameters ──────────────────────────────────────
BREAKOUT_PERIOD   = 20           # N-bar high/low breakout lookback
RSI_PERIOD        = 14
RSI_OVERSOLD      = 35           # below = BUY zone
RSI_OVERBOUGHT    = 65           # above = SELL zone
VOLUME_SURGE      = 1.5          # 1.5x = 50% above average volume
MACD_FAST         = 12
MACD_SLOW         = 26
MACD_SIGNAL       = 9
SUPERTREND_PERIOD = 10
SUPERTREND_MULT   = 3.0          # ATR multiplier

# ── LTP Watchlist (sent when market is closed) ───────────────
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

# yfinance uses .NS suffix — auto-converted below
LTP_YF = [s.replace("NSE:", "") + ".NS" for s in LTP_WATCHLIST]

# ── Full Scan Watchlist (200+ stocks) ────────────────────────
WATCHLIST = [
    # NIFTY 50
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","ITC.NS","KOTAKBANK.NS","LT.NS","SBIN.NS",
    "AXISBANK.NS","BHARTIARTL.NS","BAJFINANCE.NS","MARUTI.NS","WIPRO.NS",
    "HCLTECH.NS","ASIANPAINT.NS","SUNPHARMA.NS","ULTRACEMCO.NS","TITAN.NS",
    "BAJAJFINSV.NS","NESTLEIND.NS","POWERGRID.NS","NTPC.NS","TECHM.NS",
    "TATAMOTORS.NS","TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","ONGC.NS",
    "COALINDIA.NS","BPCL.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS",
    "EICHERMOT.NS","HEROMOTOCO.NS","BAJAJ-AUTO.NS","BRITANNIA.NS","GRASIM.NS",
    "ADANIENT.NS","ADANIPORTS.NS","INDUSINDBK.NS","M&M.NS","TATACONSUM.NS",
    "APOLLOHOSP.NS","LTIM.NS","HDFCLIFE.NS","SBILIFE.NS","SHRIRAMFIN.NS",
    # NIFTY NEXT 50
    "AMBUJACEM.NS","AUROPHARMA.NS","BANDHANBNK.NS","BERGEPAINT.NS",
    "BIOCON.NS","BOSCHLTD.NS","CANBK.NS","CHOLAFIN.NS","COLPAL.NS",
    "DABUR.NS","DLF.NS","FEDERALBNK.NS","GAIL.NS","GODREJCP.NS",
    "HAVELLS.NS","ICICIGI.NS","ICICIPRULI.NS","INDUSTOWER.NS","IOC.NS",
    "IRCTC.NS","JINDALSTEL.NS","LUPIN.NS","MARICO.NS","MCDOWELL-N.NS",
    "MPHASIS.NS","MRF.NS","NAUKRI.NS","NMDC.NS","OBEROIRLTY.NS",
    "PAGEIND.NS","PERSISTENT.NS","PIDILITIND.NS","PIIND.NS","PNB.NS",
    "SAIL.NS","SIEMENS.NS","SRF.NS","TORNTPHARM.NS","TRENT.NS",
    "TVSMOTOR.NS","VEDL.NS","VOLTAS.NS",
    # MIDCAP
    "ABCAPITAL.NS","ALKEM.NS","ASTRAL.NS","AUBANK.NS","BALKRISIND.NS",
    "BANKBARODA.NS","BATAINDIA.NS","BEL.NS","BHEL.NS","CANFINHOME.NS",
    "CEATLTD.NS","COFORGE.NS","CONCOR.NS","CROMPTON.NS","DEEPAKNTR.NS",
    "DIXON.NS","ESCORTS.NS","EXIDEIND.NS","FORTIS.NS","GLENMARK.NS",
    "GODREJPROP.NS","GRANULES.NS","HAPPSTMNDS.NS","IDFCFIRSTB.NS","IEX.NS",
    "INDHOTEL.NS","INDIAMART.NS","IRFC.NS","JKCEMENT.NS","KALYANKJIL.NS",
    "KAYNES.NS","KEI.NS","KPITTECH.NS","LALPATHLAB.NS","LATENTVIEW.NS",
    "MAPMYINDIA.NS","MASTEK.NS","METROPOLIS.NS","MOTHERSON.NS","NATCOPHARM.NS",
    "NBCC.NS","OLECTRA.NS","PHOENIXLTD.NS","POLYCAB.NS","POONAWALLA.NS",
    "RADICO.NS","RAILTEL.NS","RAMCOCEM.NS","ROUTE.NS","SCHAEFFLER.NS",
    "SOBHA.NS","SOLARINDS.NS","SONACOMS.NS","STLTECH.NS","TANLA.NS",
    "TATACHEM.NS","TATACOMM.NS","TATAELXSI.NS","TATAPOWER.NS","TEAMLEASE.NS",
    "THERMAX.NS","TIMKEN.NS","TORNTPOWER.NS","UJJIVANSFB.NS","UNOMINDA.NS",
    "VBL.NS","VINATIORGA.NS","WELCORP.NS","ZOMATO.NS","ETERNAL.NS",
    # INDEX ETFs
    "NIFTYBEES.NS","BANKBEES.NS","JUNIORBEES.NS",
]

# ═══════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════
last_alert    = {}
signals_today = []
ltp_sent      = False
eod_sent      = False

# ═══════════════════════════════════════════════════════════════
#  TELEGRAM — uses OpenClaw CLI (no webhook needed)
# ═══════════════════════════════════════════════════════════════
def send_telegram(msg):
    """Send message to Telegram via OpenClaw CLI."""
    try:
        result = subprocess.run([
            "openclaw", "message", "send",
            "--channel", "telegram",
            "--target",  TELEGRAM_CHAT_ID,
            "--message", msg
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            print(f"  [✅ TELEGRAM] {msg[:60]}...")
        else:
            print(f"  [❌ TELEGRAM ERROR] {result.stderr[:100]}")
    except Exception as e:
        print(f"  [❌ TELEGRAM EXCEPTION] {e}")

# ═══════════════════════════════════════════════════════════════
#  INDICATORS
# ═══════════════════════════════════════════════════════════════

def calc_rsi(series, period=14):
    """Relative Strength Index."""
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(series, fast=12, slow=26, signal=9):
    """MACD Line, Signal Line, Histogram."""
    ema_fast   = series.ewm(span=fast,   adjust=False).mean()
    ema_slow   = series.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line= macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_supertrend(df, period=10, multiplier=3.0):
    """
    Supertrend indicator.
    Returns Series: +1 = uptrend (BUY), -1 = downtrend (SELL)
    """
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    # ATR
    tr    = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr   = tr.rolling(period).mean()

    hl2   = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    supertrend = pd.Series(index=close.index, dtype=float)
    direction  = pd.Series(index=close.index, dtype=int)

    for i in range(1, len(close)):
        # Upper band
        if upper.iloc[i] < upper.iloc[i-1] or close.iloc[i-1] > upper.iloc[i-1]:
            upper.iloc[i] = upper.iloc[i]
        else:
            upper.iloc[i] = upper.iloc[i-1]

        # Lower band
        if lower.iloc[i] > lower.iloc[i-1] or close.iloc[i-1] < lower.iloc[i-1]:
            lower.iloc[i] = lower.iloc[i]
        else:
            lower.iloc[i] = lower.iloc[i-1]

        # Direction
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1    # uptrend
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1   # downtrend
        else:
            direction.iloc[i] = direction.iloc[i-1]

        supertrend.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]

    return direction


def calc_all_signals(df):
    """
    Run all strategies on a dataframe.
    Returns dict of signal flags + values, or None if insufficient data.
    """
    if df is None or len(df) < max(BREAKOUT_PERIOD, MACD_SLOW, SUPERTREND_PERIOD) + 10:
        return None

    close  = df["Close"].astype(float)
    high   = df["High"].astype(float)
    low    = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    # ── Price Breakout ───────────────────────────────────────
    period_high   = high.iloc[-(BREAKOUT_PERIOD+1):-1].max()
    period_low    = low.iloc[-(BREAKOUT_PERIOD+1):-1].min()
    price         = float(close.iloc[-1])
    breakout_buy  = price > float(period_high)
    breakout_sell = price < float(period_low)

    # ── RSI ──────────────────────────────────────────────────
    rsi           = calc_rsi(close, RSI_PERIOD)
    rsi_now       = float(rsi.iloc[-1])
    rsi_buy       = rsi_now < RSI_OVERSOLD
    rsi_sell      = rsi_now > RSI_OVERBOUGHT

    # ── MACD ─────────────────────────────────────────────────
    macd_line, signal_line, histogram = calc_macd(
        close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    # Crossover: MACD crossed above signal = bullish
    macd_cross_up   = (float(macd_line.iloc[-2]) < float(signal_line.iloc[-2])) and \
                      (float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]))
    # Crossover: MACD crossed below signal = bearish
    macd_cross_down = (float(macd_line.iloc[-2]) > float(signal_line.iloc[-2])) and \
                      (float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]))
    macd_histogram  = float(histogram.iloc[-1])
    macd_val        = float(macd_line.iloc[-1])
    macd_sig_val    = float(signal_line.iloc[-1])

    # ── Supertrend ───────────────────────────────────────────
    st_direction    = calc_supertrend(df, SUPERTREND_PERIOD, SUPERTREND_MULT)
    st_now          = int(st_direction.iloc[-1])   # +1 up, -1 down
    st_prev         = int(st_direction.iloc[-2])
    st_flip_up      = st_prev == -1 and st_now == 1   # just flipped bullish
    st_flip_down    = st_prev ==  1 and st_now == -1  # just flipped bearish

    # ── Volume Surge ─────────────────────────────────────────
    avg_vol   = float(volume.iloc[-20:-1].mean())
    curr_vol  = float(volume.iloc[-1])
    vol_surge = curr_vol > avg_vol * VOLUME_SURGE
    vol_x     = round(curr_vol / avg_vol, 1) if avg_vol > 0 else 0

    # ── Price Change ─────────────────────────────────────────
    prev_close  = float(close.iloc[-2])
    change_pct  = ((price - prev_close) / prev_close) * 100

    # ── Combined Signal Scoring ───────────────────────────────
    # Each confirmed strategy adds to score
    buy_score  = sum([breakout_buy, rsi_buy,  macd_cross_up,   st_flip_up,   vol_surge])
    sell_score = sum([breakout_sell,rsi_sell, macd_cross_down, st_flip_down, vol_surge])

    return {
        # Prices
        "price"         : round(price, 2),
        "period_high"   : round(float(period_high), 2),
        "period_low"    : round(float(period_low), 2),
        "change_pct"    : round(change_pct, 2),
        # RSI
        "rsi"           : round(rsi_now, 1),
        "rsi_buy"       : rsi_buy,
        "rsi_sell"      : rsi_sell,
        # MACD
        "macd"          : round(macd_val, 3),
        "macd_signal"   : round(macd_sig_val, 3),
        "macd_hist"     : round(macd_histogram, 3),
        "macd_cross_up" : macd_cross_up,
        "macd_cross_down":macd_cross_down,
        # Supertrend
        "st_direction"  : st_now,
        "st_flip_up"    : st_flip_up,
        "st_flip_down"  : st_flip_down,
        # Volume
        "vol_surge"     : vol_surge,
        "vol_x"         : vol_x,
        "avg_vol"       : int(avg_vol),
        "curr_vol"      : int(curr_vol),
        # Breakout
        "breakout_buy"  : breakout_buy,
        "breakout_sell" : breakout_sell,
        # Scores (how many strategies agree)
        "buy_score"     : buy_score,
        "sell_score"    : sell_score,
    }

# ═══════════════════════════════════════════════════════════════
#  SIGNAL TYPE CLASSIFIER
# ═══════════════════════════════════════════════════════════════
def classify_signal(sig):
    """
    Returns (signal_type, emoji) based on strategy confluence.
    Higher score = more strategies agree = stronger signal.
    """
    bs = sig["buy_score"]
    ss = sig["sell_score"]

    # Need at least 2 strategies to agree for a signal
    if bs >= 3:
        return "🚀 STRONG BUY",   "🚀"
    elif bs == 2:
        # Which 2 strategies?
        if sig["macd_cross_up"] and sig["st_flip_up"]:
            return "📈 MACD+ST BUY",  "📈"
        elif sig["breakout_buy"] and sig["vol_surge"]:
            return "⚡ BREAKOUT BUY", "⚡"
        elif sig["rsi_buy"] and sig["macd_cross_up"]:
            return "🟢 RSI+MACD BUY", "🟢"
        else:
            return "📈 BUY",          "📈"
    elif ss >= 3:
        return "🔴 STRONG SELL",  "🔴"
    elif ss == 2:
        if sig["macd_cross_down"] and sig["st_flip_down"]:
            return "📉 MACD+ST SELL",  "📉"
        elif sig["breakout_sell"] and sig["vol_surge"]:
            return "⚡ BREAKOUT SELL", "⚡"
        elif sig["rsi_sell"] and sig["macd_cross_down"]:
            return "🔻 RSI+MACD SELL", "🔻"
        else:
            return "📉 SELL",          "📉"
    # Single strategy signals (lower confidence)
    elif sig["st_flip_up"]:
        return "🟡 SUPERTREND BUY",  "🟡"
    elif sig["st_flip_down"]:
        return "🟡 SUPERTREND SELL", "🟡"
    elif sig["macd_cross_up"]:
        return "🔵 MACD BUY",  "🔵"
    elif sig["macd_cross_down"]:
        return "🔵 MACD SELL", "🔵"

    return None, None

# ═══════════════════════════════════════════════════════════════
#  ALERT FORMATTER
# ═══════════════════════════════════════════════════════════════
def format_alert(symbol, signal_type, sig):
    name     = symbol.replace(".NS", "")
    macd_dir = "▲" if sig["macd_hist"] > 0 else "▼"
    st_icon  = "↑ Uptrend" if sig["st_direction"] == 1 else "↓ Downtrend"

    # Which strategies triggered
    triggered = []
    if sig["breakout_buy"]   or sig["breakout_sell"]  : triggered.append("Breakout")
    if sig["rsi_buy"]        or sig["rsi_sell"]        : triggered.append(f"RSI({sig['rsi']:.0f})")
    if sig["macd_cross_up"]  or sig["macd_cross_down"] : triggered.append("MACD Cross")
    if sig["st_flip_up"]     or sig["st_flip_down"]    : triggered.append("Supertrend Flip")
    if sig["vol_surge"]                                 : triggered.append(f"Vol {sig['vol_x']}x")

    return (
        f"{signal_type}\n"
        f"📌 *{name}*\n"
        f"─────────────────────\n"
        f"💰 Price   : ₹{sig['price']:,.2f} ({sig['change_pct']:+.2f}%)\n"
        f"📊 RSI     : {sig['rsi']:.1f}\n"
        f"📉 MACD    : {sig['macd']:.2f} {macd_dir} Hist:{sig['macd_hist']:.2f}\n"
        f"🌀 Supertrd: {st_icon}\n"
        f"🔺 {BREAKOUT_PERIOD}H High : ₹{sig['period_high']:,.2f}\n"
        f"🔻 {BREAKOUT_PERIOD}H Low  : ₹{sig['period_low']:,.2f}\n"
        f"📦 Volume  : {sig['vol_x']:.1f}x avg\n"
        f"✅ Signals : {' | '.join(triggered)}\n"
        f"⏰ Time    : {datetime.now().strftime('%H:%M:%S')}"
    )

# ═══════════════════════════════════════════════════════════════
#  BATCH DOWNLOAD — the key to 15-20x speed
# ═══════════════════════════════════════════════════════════════
def batch_download(symbols, period="5d", interval="15m"):
    try:
        print(f"  ⚡ Batch downloading {len(symbols)} stocks...")
        t0   = time.time()
        data = yf.download(
            tickers     = symbols,
            period      = period,
            interval    = interval,
            group_by    = "ticker",
            auto_adjust = True,
            progress    = False,
            threads     = True,
        )
        elapsed = time.time() - t0
        print(f"  ✅ Done in {elapsed:.1f}s ({len(symbols)/elapsed:.0f} stocks/sec)")
        return data, elapsed
    except Exception as e:
        print(f"  [ERROR] Batch download: {e}")
        return None, 0


def get_stock_df(data, symbol, total_symbols):
    """Extract single stock df from batch result."""
    try:
        if total_symbols == 1:
            return data
        if symbol in data.columns.get_level_values(0):
            return data[symbol].dropna()
        return None
    except:
        return None

# ═══════════════════════════════════════════════════════════════
#  PROCESS ALL SIGNALS
# ═══════════════════════════════════════════════════════════════
def process_all_signals(data, symbols):
    alerts_sent = 0
    now         = time.time()

    for symbol in symbols:
        df  = get_stock_df(data, symbol, len(symbols))
        sig = calc_all_signals(df)

        if sig is None:
            continue

        # Skip if in cooldown
        if (now - last_alert.get(symbol, 0)) < ALERT_COOLDOWN:
            continue

        signal_type, _ = classify_signal(sig)

        if signal_type:
            last_alert[symbol] = now
            signals_today.append({
                "time"   : datetime.now().strftime("%H:%M"),
                "symbol" : symbol.replace(".NS", ""),
                "type"   : signal_type,
                "price"  : sig["price"],
                "rsi"    : sig["rsi"],
                "score_b": sig["buy_score"],
                "score_s": sig["sell_score"],
            })
            msg = format_alert(symbol, signal_type, sig)
            send_telegram(msg)
            print(f"  🔔 {signal_type}: {symbol} @ ₹{sig['price']}")
            alerts_sent += 1
            time.sleep(0.5)   # avoid Telegram flood

    return alerts_sent

# ═══════════════════════════════════════════════════════════════
#  LTP REPORT — sent when market is closed
# ═══════════════════════════════════════════════════════════════
def send_ltp_report():
    """Fetch and send last traded prices for LTP_WATCHLIST via yfinance."""
    print(f"[INFO] Fetching LTP for {len(LTP_WATCHLIST)} stocks...")
    try:
        data = yf.download(
            tickers     = LTP_YF,
            period      = "2d",
            interval    = "1d",
            auto_adjust = True,
            progress    = False,
            threads     = True,
        )

        lines = [
            "📊 *Last Traded Prices*",
            f"📅 {datetime.now().strftime('%d %b %Y, %H:%M')} IST",
            "─────────────────────────",
        ]

        for nse_sym, yf_sym in zip(LTP_WATCHLIST, LTP_YF):
            try:
                if len(LTP_YF) == 1:
                    closes = data["Close"].dropna()
                else:
                    closes = data["Close"][yf_sym].dropna()

                if len(closes) < 2:
                    lines.append(f"• {nse_sym.replace('NSE:','')} — No data")
                    continue

                ltp    = float(closes.iloc[-1])
                prev   = float(closes.iloc[-2])
                chg    = ((ltp - prev) / prev) * 100
                arrow  = "🟢" if chg >= 0 else "🔴"
                name   = nse_sym.replace("NSE:", "")
                lines.append(f"{arrow} *{name:<12}* ₹{ltp:>10,.2f}  ({chg:+.2f}%)")

            except Exception as e:
                name = nse_sym.replace("NSE:", "")
                lines.append(f"⚪ *{name}* — Error: {str(e)[:30]}")

        lines.append("─────────────────────────")
        lines.append("🦞 *OpenClaw AlgoScanner*")

        msg = "\n".join(lines)
        send_telegram(msg)
        print("[INFO] LTP report sent to Telegram ✅")

    except Exception as e:
        err = f"❌ LTP fetch failed: {str(e)}"
        print(f"[ERROR] {err}")
        send_telegram(err)

# ═══════════════════════════════════════════════════════════════
#  EOD SUMMARY
# ═══════════════════════════════════════════════════════════════
def send_eod_summary():
    if not signals_today:
        send_telegram(
            f"📊 *EOD Summary — {datetime.now().strftime('%d %b %Y')}*\n"
            f"No signals triggered today.\n🦞 OpenClaw AlgoScanner"
        )
        return

    buys  = [s for s in signals_today if "BUY"  in s["type"]]
    sells = [s for s in signals_today if "SELL" in s["type"]]

    lines = [
        f"📊 *EOD Summary — {datetime.now().strftime('%d %b %Y')}*",
        f"Total: {len(signals_today)} | 🟢 {len(buys)} Buy | 🔴 {len(sells)} Sell",
        "─────────────────────────",
    ]
    if buys:
        lines.append("🟢 *BUY Signals:*")
        for s in buys:
            lines.append(f"  • {s['symbol']:<12} ₹{s['price']:,.2f}  [{s['time']}]  {s['type']}")
    if sells:
        lines.append("🔴 *SELL Signals:*")
        for s in sells:
            lines.append(f"  • {s['symbol']:<12} ₹{s['price']:,.2f}  [{s['time']}]  {s['type']}")

    lines.append("─────────────────────────")
    lines.append("🦞 *OpenClaw AlgoScanner*")
    send_telegram("\n".join(lines))

# ═══════════════════════════════════════════════════════════════
#  MARKET HOURS
# ═══════════════════════════════════════════════════════════════
def is_market_open():
    now     = datetime.now()
    if now.weekday() >= 5:       # Sat/Sun closed
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)

def is_just_closed():
    now     = datetime.now()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (15 * 60 + 30) < minutes <= (15 * 60 + 35)

# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════
def main():
    global ltp_sent, eod_sent

    print("=" * 62)
    print("  ⚡ OpenClaw NSE AlgoScanner — Complete Edition")
    print(f"  Stocks    : {len(WATCHLIST)} (scan) + {len(LTP_WATCHLIST)} (LTP)")
    print(f"  Strategies: Breakout + RSI + MACD + Supertrend")
    print(f"  Interval  : {SCAN_INTERVAL}s during market hours")
    print(f"  Telegram  : Chat {TELEGRAM_CHAT_ID}")
    print("=" * 62 + "\n")

    send_telegram(
        f"⚡ *AlgoScanner Started*\n"
        f"📊 Watching {len(WATCHLIST)} NSE stocks\n"
        f"🧠 Strategies: Breakout | RSI | MACD | Supertrend\n"
        f"⏰ {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"
    )

    while True:
        now = datetime.now()

        # ── Market Open → scan all stocks ────────────────────
        if is_market_open():
            ltp_sent = False
            eod_sent = False

            print(f"\n[{now.strftime('%H:%M:%S')}] 🔍 Scanning {len(WATCHLIST)} stocks...")
            data, elapsed = batch_download(WATCHLIST, period="5d", interval="15m")

            if data is not None and not data.empty:
                alerts = process_all_signals(data, WATCHLIST)
                print(f"  📊 {elapsed:.1f}s | Signals: {alerts} | Today total: {len(signals_today)}")
            else:
                print("  [WARN] No data received from yfinance")

            time.sleep(SCAN_INTERVAL)

        # ── Just Closed → EOD summary ─────────────────────────
        elif is_just_closed() and not eod_sent:
            print(f"\n[{now.strftime('%H:%M:%S')}] 📊 Market closed — sending EOD summary")
            send_eod_summary()
            eod_sent = True
            time.sleep(60)

        # ── Market Closed → send LTP once ────────────────────
        else:
            if not ltp_sent:
                print(f"\n[{now.strftime('%H:%M:%S')}] 📊 Market closed — sending LTP report")
                send_ltp_report()
                ltp_sent = True

            print(f"[{now.strftime('%H:%M:%S')}] 💤 Market closed. Next open: Mon–Fri 09:15 IST")
            time.sleep(300)    # recheck every 5 min


if __name__ == "__main__":
    main()
