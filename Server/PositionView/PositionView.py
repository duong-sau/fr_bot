import sys
import ccxt
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from Core.Exchange.Exchange import ExchangeManager
from Core.Tracker.BitgetTracker import BitgetTracker
from Core.Tracker.GateIOTracker import GateIOTracker
from Define import exchange1, exchange2
from Server.PositionView.FrAbitrageCore import FrAbitrageCore


exchange_manager = ExchangeManager(exchange1, exchange2)

class PositionView:
    def __init__(self):
        self.tracker = BitgetTracker(exchange_manager.bitget_exchange)
        self.bitget_tracker = GateIOTracker(exchange_manager.gate_exchange)
        self.fr_arbitrage_core = FrAbitrageCore()

    def refresh(self):


        binance_open_positions = self.tracker.get_open_positions()
        bitget_open_positions = self.bitget_tracker.get_open_positions()
        self.fr_arbitrage_core.check_position(binance_open_positions + bitget_open_positions)

    def refresh_unreal_pnl(self):
        client = ccxt.bitget({'options': {
            'defaultType': 'future',  # Đảm bảo đang làm việc với futures
        }})

        for pos in self.fr_arbitrage_core.positions:
            symbol = pos.long_position.symbol
            ticker = client.fetch_ticker(symbol)
            mark_price = ticker.get('markPrice') or ticker.get('last')
            entry_price = float(pos.long_position.entry_price)
            amount = round(float(pos.long_position.amount * mark_price), 2)
            pos.long_position.amount_ = amount
            # Assuming long position; for short, reverse the calculation
            unreal_pnl = (mark_price - entry_price) / entry_price * 100 * pos.long_position.margin
            pos.unreal_pnl = round(unreal_pnl, 2)
            pos.long_position.unreal_pnl = round(unreal_pnl, 2)

    def get_core_positions(self):
        return self.fr_arbitrage_core.positions

