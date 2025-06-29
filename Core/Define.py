from enum import Enum

class EXCHANGE(Enum):
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    BITGET = "BITGET"
    BITGET_SUB = "BITGET_SUB"
    OKX = "OKX"
    GATE = "GATE"

def convert_exchange_name_to_exchange(exchange_name):
    """
    Convert exchange name to exchange object.
    """
    if exchange_name == 'binance':
        return EXCHANGE.BINANCE
    elif exchange_name == 'bitget':
        return EXCHANGE.BITGET
    elif exchange_name == 'bitget_sub':
        return EXCHANGE.BITGET_SUB
    elif exchange_name == 'gate':
        return EXCHANGE.GATE
    else:
        raise ValueError(f"Invalid exchange name: {exchange_name}")

def convert_exchange_to_name(exchange):
    """
    Convert exchange object to exchange name.
    """
    if exchange == EXCHANGE.BINANCE:
        return 'binance'
    elif exchange == EXCHANGE.BITGET:
        return 'bitget'
    elif exchange == EXCHANGE.BITGET_SUB:
        return 'bitget_sub'
    elif exchange == EXCHANGE.GATE:
        return 'gate'
    else:
        raise ValueError(f"Invalid exchange: {exchange}")

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Position:
    def __init__(self, symbol, side, amount, entry_price, exchange, margin):
        self.symbol = symbol
        self.side = side  # 'LONG' or 'SHORT'
        self.amount = amount
        self.entry_price = entry_price
        self.exchange = exchange
        self.margin = margin
        self.paid_funding = 0.0

    def __repr__(self):
        return f"Position(symbol={self.symbol}, side={self.side}, amount={self.amount}, margin={self.margin},entry_price={self.entry_price})"

    def set_paid_funding(self, paid_funding):
        self.paid_funding = paid_funding