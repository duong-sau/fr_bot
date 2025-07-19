import os
import sys
import time
from ccxt import ExchangeError
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Core")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Console_")))

import Exchange.Exchange
from Define import adl_log_path
from Tool import try_this, write_log

bitget_pro = Exchange.Exchange.bitget_pro
gate_pro = Exchange.Exchange.gate_pro

bitget_exchange = Exchange.Exchange.bitget_exchange
gate_exchange = Exchange.Exchange.gate_exchange

def adl_log(message):
    sys_log = adl_log_path
    write_log(message, sys_log)

def close_position_gate( symbol, hold_side, diff):
    order = try_this(gate_exchange.createOrder,
                     params={'symbol': symbol,
                             'type': 'market',
                             'side': 'sell' if hold_side == 'LONG' else 'buy',
                             'amount': diff,
                             'params': {
                                 'reduceOnly': True,
                                }
                             },
                     log_func=adl_log, retries=5, delay=2)
    adl_log(order)

def close_position_bitget(symbol, hold_side, diff):
    order = try_this(bitget_exchange.createOrder,
                     params={'symbol': symbol,
                             'type': 'market',
                             'side': 'SELL' if hold_side == 'LONG' else 'BUY',
                             'amount': diff,
                             'params': {
                                 'reduceOnly': True,
                                }
                             },
                     log_func=adl_log, retries=5, delay=2)
    adl_log(order)


def check_position_change(symbol):
    bitget_position = bitget_exchange.fetch_position(symbol)
    adl_log(f"Current position: {bitget_position}")
    if bitget_position['side'] is None:
        bitget_total = 0
    else:
        bitget_total = float(bitget_position['contracts']) * float(bitget_position['contractSize'])

    try:
        gate_position = gate_exchange.fetch_position(symbol)
        adl_log(f"Current position: {gate_position}")
        gate_total = float(gate_position['contracts']) * float(gate_position['contractSize'])
    except ExchangeError as e:
        adl_log(f"HTTP error occurred: {e}")
        if "POSITION_NOT_FOUND" in str(e.args[0]):
            gate_total = 0
        else:
            raise e

    if gate_total == 0 and bitget_total == 0:
        return

    bitget_side = bitget_position['info']['holdSide'].upper()
    if bitget_side == "LONG":
        gate_side = "SHORT"
    else:
        gate_side = "LONG"

    adl_log(f"Gate total: {gate_total}, Bitget total: {bitget_total}, Symbol: {symbol}, Gate side: {gate_side}, Bitget side: {bitget_side}")

    if gate_total > bitget_total:
        diff = gate_total - bitget_total
        adl_log(f"Gate has more position: {diff} {symbol}")
        close_position_gate(symbol, gate_side, diff)
    elif bitget_total > gate_total:
        diff = bitget_total - gate_total
        adl_log(f"Bitget has more position: {diff} {symbol}")
        close_position_bitget(symbol, bitget_side, diff)

lock = asyncio.Lock()
positions = {}

async def sync_hedge(exchange, symbols):
    await exchange.load_markets()
    adl_log(f"Listening for position changes on {exchange.id}...")

    while True:
        try:

            pos = await exchange.watch_positions(symbols=symbols)
            print(pos)
            for p in pos:
                p_symbol = p['symbol']
                p_size = float(p['contracts']) * float(p['contractSize'])

                async with lock:
                    if p_symbol not in positions:
                        positions[p_symbol] = {
                            'gate_size': p_size,
                            'bitget_size': p_size,
                        }
                old_bitget_size = positions[p_symbol]['bitget_size']
                old_gate_size = positions[p_symbol]['gate_size']

                async with lock:
                    if exchange.id == 'bitget':
                        positions[p_symbol]['bitget_size'] = p_size
                    elif exchange.id == 'gateio':
                        positions[p_symbol]['gate_size'] = p_size
                    else:
                        adl_log(f"Unknown exchange id: {exchange.id}")
                        sys.exit(1)

                if exchange.id == 'bitget':
                    if  old_bitget_size != p_size:
                        adl_log(f"Bitget position changed for {p_symbol}: {old_bitget_size} -> {p_size}")
                        try_this(check_position_change, params={'symbol': p_symbol}, log_func=adl_log, retries=5, delay=1)
                    positions[p_symbol]['bitget_size'] = p_size
                elif exchange.id == 'gateio':
                    if old_gate_size != p_size:
                        adl_log(f"GateIO position changed for {p_symbol}: {old_gate_size} -> {p_size}")
                        try_this(check_position_change, params={'symbol': p_symbol}, log_func=adl_log, retries=5, delay=1)
                else:
                    adl_log(f"Unknown exchange id: {exchange.id}")
                    sys.exit(1)

        except Exception as e:
            adl_log(f"Lỗi khi sync: {e}")
            time.sleep(1)



async def main():
    symbols = ["APE/USDT:USDT", "KAS/USDT:USDT", "VOXEL/USDT:USDT", "RVN/USDT:USDT", "FUN/USDT:USDT", "F/USDT:USDT", "SAHARA/USDT:USDT", "SXP/USDT:USDT", "NEWT/USDT:USDT"]
    await asyncio.gather(
        sync_hedge(gate_pro, symbols),
        sync_hedge(bitget_pro, symbols),
    )


if __name__ == '__main__':
    pos = bitget_exchange.fetch_position('NEWT/USDT:USDT')
    print(pos)
    exit(0)
    asyncio.run(main())
