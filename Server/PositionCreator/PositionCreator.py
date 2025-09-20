import math
import sys
import ccxt
import os

from Core.Tool import round_keep_n_digits

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from Core.Exchange.Exchange import ExchangeManager
from Core.Tracker.BitgetTracker import BitgetTracker
from Core.Tracker.GateIOTracker import GateIOTracker
from Define import exchange1, exchange2

exchange_manager = ExchangeManager(exchange1, exchange2)

class PositionCreator:
    def __init__(self):
        self.bitget = exchange_manager.bitget_exchange
        self.gate = exchange_manager.gate_exchange


    def open_position(self, symbol, amount):
        print("open position:", symbol, amount)

    def estimate_position(self, symbol, size):
        try:
            # Get current price from Bitget and Gate exchanges
            bitget_price = self.bitget.fetch_ticker(symbol)['last']
            gate_price = self.gate.fetch_ticker(symbol)['last']

            # Calculate the amount to buy/sell on each exchange
            estimate_amount = int(size / bitget_price)

            amount = round_keep_n_digits(estimate_amount, 2)
            print("will open position:", symbol, amount, bitget_price, gate_price)
            if amount <= 0:
                raise ValueError("The calculated amount is too small to open a position.")
            # Place a buy order on Bitget
            return True, str(amount)
        except Exception as e:
            print(f"Error opening position for {symbol}: {e}")
            return False, str(e)

