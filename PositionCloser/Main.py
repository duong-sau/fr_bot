import os
import sys

import ccxt.pro
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import Config
from Core.Define import convert_symbol


long_last_price = 0
short_last_price = 0


async def fetch_order_book(exchange, exchange_name, symbol, side):
    global long_last_price, short_last_price
    try:
        while True:
            # Lấy dữ liệu order book từ WebSocket
            converted_symbol = convert_symbol(exchange_name, symbol)
            order_book = await exchange.watch_order_book(converted_symbol, limit=100)
            if side == "BUY":
                long_last_price = float(order_book['bids'][0][0])  # Giá bid
            else:
                short_last_price = float(order_book['asks'][0][0])  # Giá ask
    except Exception as e:
        print(f"Error for {symbol}: {e}")

async def compute_spread(symbol):
    while True:
        print("\033[2J\033[H", end='')
        print(f"{'Symbol':<15} {'BID':<15} {'ASK':<15} {'SPREAD (%)':<10}")
        print("=" * 50)

        bid  = long_last_price
        ask = short_last_price

        bid_display = f"{bid:.6f}" if bid is not None else 'N/A'
        ask_display = f"{ask:.6f}" if ask is not None else 'N/A'

        spread = bid - ask if bid is not None and ask is not None else 0
        spread_percent = (spread / bid * 100) if bid else 0

        print(f"{symbol:<15} {bid_display:<15} {ask_display:<15} {round(spread_percent, 5):<10}")
        print("\n" + "=" * 50)
        await asyncio.sleep(0.1)

async def smart_close_position(long_exchange, short_exchange, symbol, min_close_rate):
    return
    global long_last_price, short_last_price
    spread = (long_last_price - short_last_price) / short_last_price

    max_close_volume = 100
    if spread > min_close_rate:
        converted_symbol = convert_symbol('gate', symbol)
        long_exchange.create_order_ws(symbol=converted_symbol, type='market', side="SELL", amount=max_close_volume)
        converted_symbol = converted_symbol('bitget', symbol)
        short_exchange.create_order_ws(symbol=converted_symbol, type='market', side="BUY", amount=max_close_volume)



async def main():
    symbol = "BTC/USDT"
    min_close_rate = 0.01  # Tỷ lệ chênh lệch tối thiểu để đóng vị thế

    # Tạo instance của ccxt
    long_exchange = ccxt.pro.bitget({
        'apiKey': Config.gate_api_key,
        'secret': Config.gate_api_secret,
        'options': {'defaultType': 'swap'}
    })

    short_exchange = ccxt.pro.gateio({
            'apiKey': Config.bitget_api_key,
            'secret': Config.bitget_api_secret,
            'passphrase': Config.bitget_password,
            'options': {'defaultType': 'swap'}
         })

    # converted_symbol = convert_symbol('bitget', symbol)
    # response = await long_exchange.create_order_ws(symbol=converted_symbol, type='market', side="SELL", amount=0.01)
    # print(response)
    converted_symbol = convert_symbol('gate', symbol)
    res = await short_exchange.create_order_ws(symbol=converted_symbol, type='market', side="buy", amount=-0.0001)
    print(res)

    sys.exit(0)

    tasks = [
        fetch_order_book(long_exchange, "bitget", symbol, "BUY"),
             fetch_order_book(short_exchange, "gate", symbol, "SELL"),
             compute_spread(symbol),
             smart_close_position(long_exchange, short_exchange, symbol, min_close_rate)
    ]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())