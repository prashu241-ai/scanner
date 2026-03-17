# get_ltp_test.py

import sys
import yfinance as yf

# --- Watchlist ---
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
]

def convert_symbol(symbol):
    """
    Convert Kite symbol format (NSE:RELIANCE)
    to Yahoo Finance format (RELIANCE.NS)
    """
    if ":" in symbol:
        stock = symbol.split(":")[1]
        return f"{stock}.NS"
    return symbol

def fetch_ltps(symbols):
    """
    Fetch LTP using yfinance
    """
    print("Fetching Last Traded Prices (via yfinance)")
    print("-" * 50)

    for symbol in symbols:
        try:
            yf_symbol = convert_symbol(symbol)

            ticker = yf.Ticker(yf_symbol)
            price = ticker.fast_info["lastPrice"]

            print(f"{symbol:<30} : ₹{price}")

        except Exception as e:
            print(f"{symbol:<30} : Error fetching price ({e})")

if __name__ == "__main__":
    fetch_ltps(WATCHLIST)
