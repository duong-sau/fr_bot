from ccxt import ExchangeError

from Core.Tool import try_this
from MainProcess.ADLControl.Log import adl_log


def close_position_gate(gate_exchange, symbol, hold_side, diff):
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

def close_position_bitget(bitget_exchange, symbol, hold_side, diff):
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

def fetch_position_gate(gate_exchange, symbol):
    try:
        gate_position = gate_exchange.fetch_position(symbol)
        print(f"Current position: {gate_position}")
        gate_total = float(gate_position['contracts']) * float(gate_position['contractSize'])
        gate_side = gate_position['side'] if gate_position['side'] else None
        contract_size = gate_position['contractSize']
        return gate_total, gate_side, contract_size
    except ExchangeError as e:
        adl_log(f"HTTP error occurred: {e}")
        if "POSITION_NOT_FOUND" in str(e.args[0]):
            gate_total = 0
            gate_side = None
            contract_size = None
            return gate_total, gate_side, contract_size
        else:
            raise e

def fetch_position_bitget(bitget_exchange, symbol):
    bitget_position= bitget_exchange.fetch_position(symbol)
    print(f"Current position: {bitget_position}")
    if bitget_position['side'] is None:
        bitget_total = 0
        bitget_side = None
        contract_size = None
    else:
        bitget_total = float(bitget_position['contracts']) * float(bitget_position['contractSize'])
        bitget_side = bitget_position['side']
        contract_size = bitget_position['contractSize']
    return bitget_total, bitget_side, contract_size