from enum import Enum

class EXCHANGE(Enum):
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    BITGET = "BITGET"
    OKX = "OKX"
    GATE = "GATE"


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