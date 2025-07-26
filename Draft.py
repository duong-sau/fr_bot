import sys

import ccxt.pro
import asyncio

from Exchange.Exchange import gate_exchange, bitget_exchange

gate = gate_exchange
bitget =bitget_exchange

async def close_long_gate(symbol):
    """
    Đóng lệnh LONG trên Gate
    """
    try:
        gate.createOrder(symbol="SXP/USDT:USDT",type='market', side='sell', amount=10, params={'reduceOnly': True})
    except Exception as e:
        print(f"Lỗi khi đóng lệnh LONG trên Gate cho {symbol}: {e}")

async def close_short_bitget(symbol):
    """
    Đóng lệnh SHORT trên Gate
    """
    try:
        bitget.createOrder(symbol="SXP/USDT:USDT",type='market', side='buy', amount=10, params={'reduceOnly': True})
    except Exception as e:
        print(f"Lỗi khi đóng lệnh SHORT trên Bitget cho {symbol}: {e}")

last_prices = {}

def log(message):
    file = open("log.txt", "a")
    file.write(message + "\n")
    file.close()

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

async def calculate_spreads(symbols):

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

            print(f"{symbol:<15} {bid_display:<15} {ask_display:<15} {round(spread_percent, 5):<10}")

            if symbol != "SXP/USDT":
                continue
            if bid is None or ask is None:
                pass
            elif spread_percent > - 0.1:
                log(f"Bid and Ask are equal for {symbol}: Bid={bid}, Ask={ask}")
                print(f"Bid and Ask are equal for {symbol}: Bid={bid}, Ask={ask}")
                await asyncio.gather(
                    close_short_bitget(symbol),
                    close_long_gate(symbol)
                )
                sys.exit(0)
        print("\n" + "=" * 50)

        await asyncio.sleep(0.1)

async def main():

    symbols = ["SXP/USDT"]

    # Tạo instance của ccxt
    bitget_exchange = ccxt.pro.bitget({'options': {'defaultType': 'swap'}})
    gate_exchange = ccxt.pro.gateio({'options': {'defaultType': 'swap'}})

    global last_prices
    last_prices = {symbol: {'bid': None, 'ask': None} for symbol in symbols}

    tasks = []
    for symbol in symbols:
        tasks.append(fetch_order_book(bitget_exchange, "bitget", symbol, "ASK"))
        tasks.append(fetch_order_book(gate_exchange, "gate", symbol, "BID"))

    tasks.append(calculate_spreads(symbols))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())