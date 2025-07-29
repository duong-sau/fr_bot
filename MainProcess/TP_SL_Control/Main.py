import sys
import threading
import time
import os
from ccxt import ExchangeError
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Core.Exchange.Exchange import ExchangeManager
from MainProcess.TP_SL_Control.Order import open_take_profit_bitget, open_stop_loss_bitget, open_take_profit_gate, \
    open_stop_loss_gate
from Define import tp_sl_log_path, exchange1, exchange2, tp_sl_info_path, root_path
from Core.Tool import write_log


def tp_sl_log(message):
    sys_log = tp_sl_log_path
    write_log(message, sys_log)


def auto_tp_sl(bitget, gate, symbol, tp_rate, sl_rate, interval=180):
    while True:
        bitget_symbol = "OMNI1/USDT:USDT" if symbol == "OMNI/USDT:USDT" else symbol
        bitget_position = bitget.fetch_position(bitget_symbol)
        tp_sl_log(f"Current position: {bitget_position}")
        if bitget_position['side'] is None:
            bitget_total = 0
        else:
            bitget_total = float(bitget_position['info']['total'])
        try:
            gate_position = gate.fetch_position(symbol)
            tp_sl_log(f"Current position: {gate_position}")
            gate_total = float(gate_position['info']['size'])
        except ExchangeError as e:
            tp_sl_log(f"HTTP error occurred: {e}")
            if "POSITION_NOT_FOUND" in str(e.args[0]):
                gate_total = 0
            else:
                raise e

        if gate_total == 0 or bitget_total == 0:
            return

        bitget_price = bitget.fetch_ticker(bitget_symbol)['last']
        bitget_side = bitget_position['info']['holdSide'].upper()
        if bitget_side == "LONG":
            # Bitget TP and SL for LONG position
            bitget_tp = bitget_price * (1 + tp_rate)
            bitget_sl = bitget_price * (1 - sl_rate)

            # Gate TP and SL for LONG position
            gate_tp = bitget_price * (1 - tp_rate)
            gate_sl = bitget_price * (1 + sl_rate)

            gate_side = "LONG"
        else:

            # Bitget TP and SL for SHORT position
            bitget_tp = bitget_price * (1 - tp_rate)
            bitget_sl = bitget_price * (1 + sl_rate)

            # Gate TP and SL for SHORT position
            gate_tp = bitget_price * (1 + tp_rate)
            gate_sl = bitget_price * (1 - sl_rate)

            gate_side = "SHORT"

        gate.cancelAllOrders(symbol=symbol, params={'trigger': True})
        gate_tp_order = open_take_profit_gate(gate, symbol, gate_side, gate_total, gate_tp)
        bitget_tp_order = open_take_profit_bitget(bitget, bitget_symbol, bitget_side, bitget_total, bitget_tp)

        gate_sl_order = open_stop_loss_gate(gate, symbol, "SHORT", gate_total, gate_sl)
        bitget_sl_order = open_stop_loss_bitget(bitget, bitget_symbol, bitget_side, bitget_total, bitget_sl)

        time.sleep(interval)  # Sleep for 2 minutes before checking again


if __name__ == '__main__':

    exchange_manager = ExchangeManager(exchange1, exchange2)
    bitget = exchange_manager.bitget_exchange
    gate = exchange_manager.gate_exchange

    with open(tp_sl_info_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    tp_rate = float(config['TP_SL']['tp_rate'])
    sl_rate = float(config['TP_SL']['sl_rate'])
    interval = int(config['TP_SL']['interval'])

    symbols = []
    with open(f"{root_path}/code/_settings/symbols.txt", 'r', encoding='utf-8') as file:
        lines = file.readlines()
    for line in lines:
        symbols.append(line.strip())
    print(f"Starting TP/SL control with symbols: {symbols}, TP rate: {tp_rate}, SL rate: {sl_rate}, Interval: {interval} seconds")

    threads = []
    for symbol in symbols:
        symbol_full = f"{symbol}/USDT:USDT"
        t = threading.Thread(target=auto_tp_sl, args=(bitget, gate, symbol_full, tp_rate, sl_rate, interval))
        t.start()
        threads.append(t)
        time.sleep(10)
    for t in threads:
        t.join()
