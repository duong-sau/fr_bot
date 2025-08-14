from email.policy import default
import ccxt.pro
from attr.setters import convert

from Core.Exchange.Exchange import ExchangeManager
from Define import exchange2, exchange1

exchange_manager = ExchangeManager(exchange1, exchange2)
bitget = exchange_manager.bitget_exchange
gate = exchange_manager.gate_exchange

bitget_pro = ccxt.pro.bitget({'options': {'defaultType': 'swap'}})
gate_pro = ccxt.pro.gateio({'options': {'defaultType': 'swap'}})

import asyncio

symbol = "HYPER/USDT:USDT"

def convert_symbol(exchange, symbol):
    symbol = symbol.replace(':USDT', '')
    if exchange == "bitget":
        symbol = symbol.replace("OMNI", "OMNI1")  # Chuyển OMNI/USDT -> OMNI1/USDT
        return symbol.replace("/", "")  # Chuyển BTC/USDT -> BTCUSDT
    elif exchange == "gate":
        return symbol.replace("/", "_")  # Chuyển BTC/USDT -> BTC_USDT
    elif exchange == "binance":
        return symbol.replace("/", "")
    return symbol


async def get_current_positions():
    bitget_positions = bitget.fetch_positions([convert_symbol('bitget', symbol)])
    gate_positions = gate.fetch_positions([symbol])

    # Lấy short bên bitget
    bitget_short = next(
        (pos for pos in bitget_positions if pos['symbol'] == symbol and pos['side'] == 'short'),
        None
    )

    # Lấy long bên gate
    gate_long = next(
        (pos for pos in gate_positions if pos['symbol'] == symbol and pos['side'] == 'long'),
        None
    )

    return bitget_short, gate_long


bitget_bid = 0
gate_ask = 0
async def listen_order_book_bitget(symbol):
    global bitget_bid
    while True:
        converted_symbol = convert_symbol("bitget", symbol)
        order_book = await bitget_pro.watch_order_book(converted_symbol, limit=100)
        bitget_bid = order_book['asks'][0][0]  # Giá bid
        await asyncio.sleep(0.1)

async def listen_order_book_gate(symbol):
    global gate_ask
    while True:
        converted_symbol = convert_symbol("gate", symbol)
        order_book = await gate_pro.watch_order_book(converted_symbol, limit=100)
        gate_ask = order_book['bids'][0][0]  # Giá ask
        await asyncio.sleep(0.1)

async def track_pnl_realtime():
    bitget_short, gate_long = await get_current_positions()

    if not bitget_short or not gate_long:
        print("Không tìm thấy vị thế hợp lệ!")
        return

    entry_short = float(bitget_short['entryPrice'])
    short_amt = float(bitget_short['contracts'] * bitget_short['contractSize'])  # hoặc 'amount' tùy sàn

    entry_long = float(gate_long['entryPrice'])
    long_amt = float(gate_long['contracts'] * gate_long['contractSize'])  # hoặc 'amount'

    print(f"🚀 Entry Bitget Short: {entry_short}, Amt: {short_amt}")
    print(f"🚀 Entry Gate Long: {entry_long}, Amt: {long_amt}")
    print("🎯 Đang tracking PnL realtime...")


    while True:
        try:
            mark_price_bitget = float(bitget_bid)  # dùng để đóng SHORT (bán cho người mua)
            mark_price_gate = float(gate_ask)  # dùng để đóng LONG (mua từ người bán)

            pnl_short = (entry_short - mark_price_bitget) * short_amt
            pnl_long = (mark_price_gate - entry_long) * long_amt
            total_pnl = pnl_short + pnl_long

            print(f"📉 Bitget Mark: {mark_price_bitget}, PnL Short: {round(pnl_short, 2)}")
            print(f"📈 Gate Mark:   {mark_price_gate}, PnL Long:  {round(pnl_long, 2)}")
            print(f"💰 Tổng Lãi/Lỗ: {round(total_pnl, 2)} USDT\n")

            await asyncio.sleep(0.1)

        except Exception as e:
            print(f"⚠️ Lỗi khi cập nhật PnL: {e}")
            await asyncio.sleep(3)

async def main():

    # Bắt đầu lắng nghe order book
    await asyncio.gather(
        listen_order_book_bitget(symbol),
        listen_order_book_gate(symbol),
        track_pnl_realtime()
    )

if __name__ == "__main__":
    asyncio.run(main())