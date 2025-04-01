import ccxt
import pandas as pd
import ta
from concurrent.futures import ThreadPoolExecutor
import requests
import json

# Load CoinMarketCap IDs from the JSON file
def load_coin_ids():
    try:
        with open("coin_ids.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("coin_ids.json not found. Please run the script to fetch CoinMarketCap IDs.")
        return {}

# Fetch Fear and Greed Index
def fetch_fear_and_greed_index():
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url)
        data = response.json()
        fgi = data["data"][0]
        return {
            "value": int(fgi["value"]),
            "classification": fgi["value_classification"]
        }
    except Exception as e:
        print("Error fetching Fear and Greed Index:", e)
        return {"value": None, "classification": "Unavailable"}

# Helper function to find the symbol and exchange
def find_symbol_and_exchange(coin, exchanges):
    for name, exchange in exchanges.items():
        try:
            markets = exchange.load_markets()
            for quote in ["USDT", "USD"]:
                candidate = f"{coin}/{quote}"
                if candidate in exchange.symbols:
                    return candidate, exchange
        except Exception as e:
            print(f"Error loading markets from {name}: {e}")
            continue
    return None, None

# Helper function to fetch the latest price of a coin
def get_latest_price(exchange, symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        # Format the price to avoid scientific notation
        if price is not None:
            return f"{price:.10f}".rstrip('0').rstrip('.')  # Remove trailing zeros
        else:
            return "Unavailable"
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return "Unavailable"

# Main function to analyze RSI trends
def analyze_rsi_trends():
    exchanges = {
        "binance": ccxt.binance(),
        "kucoin": ccxt.kucoin(),
        "gateio": ccxt.gateio(),
        "coinex": ccxt.coinex(),
        "mexc": ccxt.mexc(),
        "bybit": ccxt.bybit()
    }

    rsi_timeframes = {
        "Spot Macro": "1w",
        "Swing Macro": "1d",
        "Micro": "4h"
    }

    coin_list = [
        "ZEPH", "XRP", "XMR", "XLM", "WIN", "WIF", "VET", "TRVL", "TRUMP", "TIA", "TAI", "SOLAMA", "SLP", "SHIB", "SGB",
        "SEI", "SAND", "SAGA", "RSR", "BTC", "ROSE", "QNT", "PEPE", "PDEX", "PASG", "ORDI", "ORAI", "NEIRO", "MYRO", "MLN",
        "MEE", "MAZZE", "MANA", "LTC", "LOOKS", "LINK", "KSM", "KIP", "JASMY", "IOTA", "HUAHUA", "HOT", "HERO", "HBAR",
        "GPT", "GALA", "FLR", "FIRO", "FIL", "FET", "EXVG", "EWT", "ETH", "ETC", "EOS", "ENS", "ENJ", "DVPN", "DOT", "DOGE",
        "DGB", "DFI", "CVX", "CSPR", "CRV", "CELO", "CAT", "BCH", "BABYDOGE", "AVAX", "AVA", "ARB", "APE", "ALGO", "AKT",
        "ADA", "ACT", "AAVE", "1INCH"
    ]

    coin_ids = load_coin_ids()

    # Fetch the Fear and Greed Index
    fgi = fetch_fear_and_greed_index()

    def process_coin(coin):
        try:
            symbol, exchange_used = find_symbol_and_exchange(coin, exchanges)
            if not exchange_used or not symbol:
                return {"Coin": coin, "error": "Symbol not found"}

            # Fetch the latest price
            current_price = get_latest_price(exchange_used, symbol)

            # Fetch data and calculate indicators
            weekly_ohlcv = exchange_used.fetch_ohlcv(symbol, '1w', limit=100)
            daily_ohlcv = exchange_used.fetch_ohlcv(symbol, '1d', limit=400)
            df_weekly = pd.DataFrame(weekly_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df_daily = pd.DataFrame(daily_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

            ema21w = df_weekly["close"].ewm(span=21).mean().iloc[-1]
            sma300d = df_daily["close"].rolling(window=300).mean().iloc[-1]
            sma400d = df_daily["close"].rolling(window=400).mean().iloc[-1]
            price = df_daily["close"].iloc[-1]

            if pd.isna(ema21w) or pd.isna(sma300d) or pd.isna(sma400d):
                spot_macro_trend = "Waiting"
            elif ema21w > sma400d and price > ema21w:
                spot_macro_trend = "Bullish"
            elif ema21w > sma400d and price < ema21w:
                spot_macro_trend = "Neutral"
            elif ema21w < sma300d and price < sma400d and price < ema21w:
                spot_macro_trend = "Bearish"
            elif ema21w < sma300d and price > ema21w:
                spot_macro_trend = "Neutral"
            else:
                spot_macro_trend = "Waiting"
            
            icon_url = f"https://s2.coinmarketcap.com/static/img/coins/64x64/{coin_ids.get(coin, 'default')}.png"
            signals = {
                "Coin": coin,
                "icon_url": icon_url,
                "Current Price": current_price,
                "Spot Macro Trend": spot_macro_trend
            }

            for key, timeframe in rsi_timeframes.items():
                ohlcv = exchange_used.fetch_ohlcv(symbol, timeframe, limit=100)
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)

                rsi = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
                df["rsi"] = rsi

                last_rsi = df["rsi"].iloc[-1]
                signals[f"{key} RSI ({timeframe})"] = round(last_rsi, 2)

            # Spot Entry Logic
            rsi_weekly = signals.get("Spot Macro RSI (1w)", 50)  # Get RSI for Weekly timeframe
            trend_macro = signals.get("Spot Macro Trend", "Sideways")  # Get Spot Macro Trend
            fgi_value = fgi["value"]

            if rsi_weekly < 35 and trend_macro == "Bearish" and fgi_value is not None and fgi_value < 50:
                signals["Spot Entry"] = "Buy"
            else:
                signals["Spot Entry"] = "Wait"

            # Position Status Logic
            rsi_macro = signals.get("Spot Macro RSI (1w)", 50)
            trend_macro = signals.get("Spot Macro Trend", "Sideways")

            if trend_macro == "Bullish" and rsi_macro < 70:
                status = "Hold"
            elif trend_macro == "Bullish" and rsi_macro >= 70 and fgi_value is not None and fgi_value > 50:
                status = "Reduce/Look for Exit"
            elif rsi_macro <= 35 and fgi_value is not None and fgi_value < 40:
                status = "DCA"
            else:
                status = "Wait"

            signals["Position Status"] = status

            return signals

        except Exception as e:
            return {"Coin": coin, "error": str(e)}

    # Use ThreadPoolExecutor to process coins in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_coin, coin_list))

    return results