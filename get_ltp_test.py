# get_ltp_test.py

import sys
from kiteconnect import KiteConnect

# --- Kite Connect Credentials ---
# IMPORTANT: Replace with your actual credentials from breakout_scanner.py
KITE_API_KEY = "3wbhan16xjugru90"  # e.g., "3wbhan16xjugru90"
KITE_API_SECRET = "5zxg87zeoe9hennhfhnu7wp0la5p73tr" # e.g., "5zxg87zeoe9hennhfhnu7wp0la5p73tr"
KITE_ACCESS_TOKEN = "OO82eKzYFBmmcyxckMJnekgsEiNXMEIV" # e.g., "lRUsHOZRjXjPUX2vZzdTt2z6iYptwxg6"


# --- Watchlist from breakout_scanner.py ---
# This list is extracted from your breakout_scanner.py file
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
    "NSE:NIFTY 17TH MAR 23450 CE",
    "NSE:NIFTY 17TH MAR 22850 PE",
]

def fetch_ltps(api_key, api_secret, access_token, symbols):
    """
    Initializes KiteConnect, fetches LTP for given symbols, and prints results.
    """
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        print("Successfully connected to Kite.")
        print("\nFetching Last Traded Prices (LTPs):")
        print("-" * 50)

        results = {}
        errors = []

        # Fetching LTP in batches can be more efficient and avoid hitting rate limits as quickly
        # The kite.ltp() method can accept a list of symbols.
        try:
            # kite.ltp() expects a list of exchanges:symbols
            # e.g., ['NSE:RELIANCE', 'BSE:INFY']
            ltp_data = kite.ltp(symbols)

            for symbol in symbols:
                if symbol in ltp_data and ltp_data[symbol]:
                    price = ltp_data[symbol].get('last_price')
                    instrument_token = ltp_data[symbol].get('instrument_token')
                    exchange = ltp_data[symbol].get('exchange')
                    results[symbol] = {
                        'ltp': price,
                        'instrument_token': instrument_token,
                        'exchange': exchange
                    }
                else:
                    errors.append(f"{symbol}: No data found.")

        except Exception as e:
            errors.append(f"Batch LTP fetch error: {e}")

        # Print results
        for symbol, data in results.items():
            ltp_str = f"₹{data['ltp']}" if data['ltp'] is not None else "N/A"
            token_str = f"(Token: {data['instrument_token']})" if data['instrument_token'] else ""
            print(f"{symbol:<35} : {ltp_str} {token_str}")

        if errors:
            print("\n--- Errors encountered ---")
            for error in errors:
                print(error)

    except Exception as e:
        print(f"Error initializing KiteConnect or fetching data: {e}", file=sys.stderr)
        print("Please check your API Key, Secret, Access Token, and network connection.", file=sys.stderr)

if __name__ == "__main__":
    if KITE_API_KEY == "YOUR_KITE_API_KEY" or KITE_API_SECRET == "YOUR_KITE_API_SECRET" or KITE_ACCESS_TOKEN == "YOUR_KITE_ACCESS_TOKEN":
        print("Please update KITE_API_KEY, KITE_API_SECRET, and KITE_ACCESS_TOKEN in the script.",
    fetch_ltps(KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN, WATCHLIST)
