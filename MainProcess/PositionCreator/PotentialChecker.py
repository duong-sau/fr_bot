import os
import sys
import ccxt.pro
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Core.Tool import push_notification

last_prices = {}
last_prices_out = {}

def convert_symbol(exchange, symbol):
    symbol = symbol.replace(':USDT', '')
    if exchange == "bitget":
        return symbol.replace("/", "")  # Chuyển BTC/USDT -> BTCUSDT
    elif exchange == "gate":
        return symbol.replace("/", "_")  # Chuyển BTC/USDT -> BTC_USDT
    elif exchange == "binance":
        return symbol.replace("/", "")
    return symbol

async def fetch_order_book(exchange, exchange_name, symbol, side):
    global last_prices
    try:
        while True:
            # Lấy dữ liệu order book từ WebSocket
            converted_symbol = convert_symbol(exchange_name, symbol)
            order_book = await exchange.watch_order_book(converted_symbol, limit=100)
            if side == "BID":
                last_prices[symbol]['bid'] = order_book['bids'][0][0]  # Giá bid
                last_prices_out[symbol]['bid'] = order_book['asks'][0][0]
            else:
                last_prices[symbol]['ask'] = order_book['asks'][0][0]  # Giá ask
                last_prices_out[symbol]['ask'] = order_book['bids'][0][0]
    except Exception as e:
        print(f"Error for {symbol}: {e}")
spreads = []
spreads_out = []
async def calculate_spreads(symbol):
    count = 0
    while True:

        if count <=10:
            count += 1
            continue

        bid = last_prices[symbol]['bid']
        ask = last_prices[symbol]['ask']
        spread = bid - ask if bid is not None and ask is not None else 0
        spread_percent = (spread / bid * 100) if bid else 0
        spreads.append(spread_percent)

        bid_out = last_prices_out[symbol]['bid']
        ask_out = last_prices_out[symbol]['ask']
        spread_out = bid_out - ask_out if bid_out is not None and ask_out is not None else 0
        spread_out_percent = (spread_out / bid_out * 100) if bid_out else 0
        spreads_out.append(spread_out_percent)

        count += 1

        if count >= 310:
            break
        await asyncio.sleep(0.1)
    mean_spread = sum(spreads) / len(spreads) if spreads else 0
    push_notification(f"Spread for {symbol}: {round(mean_spread, 5)}%, Out: {round(sum(spreads_out) / len(spreads_out), 5)}%")
    sys.exit(0)

async def main():

    symbol = sys.argv[1]
    # Tạo instance của ccxt
    bitget_exchange = ccxt.pro.bitget({'options': {'defaultType': 'swap'}})
    gate_exchange = ccxt.pro.gateio({'options': {'defaultType': 'swap'}})

    global last_prices, last_prices_out
    last_prices = {symbol: {'bid': None, 'ask': None}}
    last_prices_out = {symbol: {'bid': None, 'ask': None}}

    tasks = []
    tasks.append(fetch_order_book(bitget_exchange, "bitget", symbol, "BID"))
    tasks.append(fetch_order_book(gate_exchange, "gate", symbol, "ASK"))

    tasks.append(calculate_spreads(symbol))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())