import krakenex
from pykrakenapi import KrakenAPI
import os
import time
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
k = krakenex.API(key=os.getenv("KRAKEN_API_KEY"), secret=os.getenv("KRAKEN_PRIVATE_KEY"))
api = KrakenAPI(k)

COINS = {
    "DOGE": "DOGECAD",
    "SHIB": "SHIBUSD",
    "BONK": "BONKUSD",
    "PEPE": "PEPEUSD",
    "FLOKI": "FLOKIUSD",
    "ETH": "ETHCAD"
}

RSI_PERIOD = 14
OVERSOLD_THRESHOLD = 30
OVERBOUGHT_THRESHOLD = 70
TRADE_PERCENTAGE = 0.75
LOG_FILE = "trade_log.csv"

def log_trade(pair, action, price, volume, balances):
    timestamp = pd.Timestamp.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "pair": pair,
        "action": action,
        "price": price,
        "volume": volume,
        "balance_snapshot": str(balances)
    }
    df = pd.DataFrame([entry])
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(LOG_FILE, index=False)
    print(f"📝 {action.upper()} {pair}: {volume} @ {price:.4f}")

def get_rsi(prices, period=RSI_PERIOD):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_balance():
    try:
        return api.get_account_balance()
    except Exception as e:
        print(f"❌ Error getting account balance: {e}")
        return {}

def trade():
    balances = get_balance()
    if not balances:
        print("⚠️ No balances found. Skipping cycle.")
        return

    for coin, pair in COINS.items():
        try:
            print(f"\n🔍 Checking {pair}...")
            ohlc, _ = api.get_ohlc_data(pair, interval=1)  # '1' = 1-minute data
            ohlc.index.freq = '1min'  # explicitly set freq to avoid warning
            close_prices = ohlc['close'].astype(float)
            rsi = get_rsi(close_prices)
            current_rsi = rsi.iloc[-1]
            current_price = close_prices.iloc[-1]

            print(f"📈 RSI for {pair}: {current_rsi:.2f} | Price: {current_price:.6f}")

            base = "ZCAD" if "CAD" in pair else "ZUSD"
            base_balance = float(balances.get(base, 0.0))
            coin_balance = float(balances.get(f"X{coin}", balances.get(coin, 0.0)))

            if current_rsi < OVERSOLD_THRESHOLD and base_balance > 1:
                volume = (base_balance * TRADE_PERCENTAGE) / current_price
                api.add_standard_order(pair=pair, type='buy', ordertype='market', volume=str(volume))
                log_trade(pair, "buy", current_price, volume, balances)

            elif current_rsi > OVERBOUGHT_THRESHOLD and coin_balance > 0:
                volume = coin_balance * TRADE_PERCENTAGE
                api.add_standard_order(pair=pair, type='sell', ordertype='market', volume=str(volume))
                log_trade(pair, "sell", current_price, volume, balances)

        except Exception as e:
            print(f"❌ Error processing {pair}: {e}")
        time.sleep(3)

if __name__ == "__main__":
    print("🚀 Starting RSI-based trading bot...")
    try:
        while True:
            trade()
            print("✅ Cycle complete. Sleeping for 60 seconds...\n")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped manually.")
Update main.py with logging + bugfixes
