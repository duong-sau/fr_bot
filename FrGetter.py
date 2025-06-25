import time
import csv
from datetime import datetime
import ccxt

SYMBOLS = ["SXPUSDT", "BMTUSDT", "MTLUSDT", "BIDUSDT"]  # Use CCXT symbol format

def get_funding_rate(exchange, symbol):
    try:
        funding = exchange.fetchFundingRate(symbol)
        if exchange.id == 'binance':
            fr = float(funding['info']['lastFundingRate']) * 100
        elif exchange.id == 'bitget':
            fr = float(funding['info']['fundingRate']) * 100
        else:
            fr = 0
        return round(fr, 4)
    except Exception as e:
        print(f"Error fetching funding rate for {symbol} on {exchange.id}: {e}")
        return float(0.0)

def main():
    binance = ccxt.binance({'options': {'defaultType': 'future'}})
    bitget = ccxt.bitget()
    bitget.options['defaultType'] = 'swap'

    while True:
        funding_rate = {}
        for symbol in SYMBOLS:
            binance_rate = get_funding_rate(binance, symbol)
            bitget_rate = get_funding_rate(bitget, symbol)
            funding_rate[symbol] = {
                'binance': binance_rate,
                'bitget': bitget_rate
            }

        print(funding_rate)

        with open('fundingrate.csv', 'w', newline='') as csvfile:
            csvfile.write(str(funding_rate))
            csvfile.flush()
        time.sleep(10)

if __name__ == '__main__':
    main()