import os

import ccxt.pro
import asyncio

from Define import root_path

last_prices = {}

def convert_symbol(exchange, symbol):
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
            else:
                last_prices[symbol]['ask'] = order_book['asks'][0][0]  # Giá ask
    except Exception as e:
        print(f"Error for {symbol}: {e}")

spreads = []
async def calculate_spreads(symbols):
    count = 0
    while True:
        print("\033[2J\033[H", end='')
        print(f"{'Symbol':<15} {'BID':<15} {'ASK':<15} {'SPREAD (%)':<10}")
        print("=" * 50)
        for symbol in symbols:
            bid = last_prices[symbol]['bid']
            ask = last_prices[symbol]['ask']

            bid_display = f"{bid:.6f}" if bid is not None else 'N/A'
            ask_display = f"{ask:.6f}" if ask is not None else 'N/A'

            spread = bid - ask if bid is not None and ask is not None else 0
            spread_percent = (spread / bid * 100) if bid else 0
            spreads.append(spread_percent)

            print(f"{symbol:<15} {bid_display:<15} {ask_display:<15} {round(spread_percent, 5):<10}")
        print("\n" + "=" * 50)
        await asyncio.sleep(0.1)

async def main():
    potential_file = os.path.join(root_path, "data/futures_symbols.txt")
    symbols = []
    with open(potential_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            symbols.append(line.strip().replace(':USDT', ''))  # Loại bỏ ':USDT' nếu có
    # Tạo instance của ccxt
    bitget_exchange = ccxt.pro.bitget({'options': {'defaultType': 'swap'}})
    gate_exchange = ccxt.pro.gateio({'options': {'defaultType': 'swap'}})

    global last_prices
    last_prices = {symbol: {'bid': None, 'ask': None} for symbol in symbols}

    tasks = []
    for symbol in symbols:
        tasks.append(fetch_order_book(bitget_exchange, "bitget", symbol, "BID"))
        tasks.append(fetch_order_book(gate_exchange, "gate", symbol, "ASK"))

    tasks.append(calculate_spreads(symbols))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())