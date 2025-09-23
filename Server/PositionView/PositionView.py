import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from Core.Exchange.Exchange import ExchangeManager
from Core.Tracker.BitgetTracker import BitgetTracker
from Core.Tracker.GateIOTracker import GateIOTracker
from Define import exchange1, exchange2
from Server.PositionView.FrAbitrageCore import FrAbitrageCore
from Core.Define import EXCHANGE


exchange_manager = ExchangeManager(exchange1, exchange2)

class PositionView:
    def __init__(self):
        self.tracker = BitgetTracker(exchange_manager.bitget_exchange)
        self.bitget_tracker = GateIOTracker(exchange_manager.gate_exchange)
        self.fr_arbitrage_core = FrAbitrageCore()

    def refresh(self):


        # Collect open positions from both trackers
        bitget_open_positions = self.tracker.get_open_positions()
        gate_open_positions = self.bitget_tracker.get_open_positions()
        self.fr_arbitrage_core.check_position(bitget_open_positions + gate_open_positions)

        # compute notional size (USDT) per position based on entry price
        bitget = exchange_manager.bitget_exchange
        gate = exchange_manager.gate_exchange
        try:
            if not getattr(bitget, 'markets', None):
                bitget.load_markets()
        except Exception:
            pass
        try:
            if not getattr(gate, 'markets', None):
                gate.load_markets()
        except Exception:
            pass

        def _to_swap_symbol(sym: str) -> str:
            try:
                s = (sym or '').upper()
                if '/USDT' in s and ':USDT' in s:
                    return s
                if s.endswith('USDT') and '/' not in s:
                    base = s[:-4]
                    return f"{base}/USDT:USDT"
                if s.endswith('/USDT') and ':USDT' not in s:
                    return s + ':USDT'
                return s
            except Exception:
                return sym

        def _contract_size_from_market(market: dict) -> float:
            cs = 1.0
            if isinstance(market, dict):
                info = market.get('info') or {}
                v = market.get('contractSize')
                if v is not None:
                    try:
                        f = float(v)
                        if f > 0:
                            return f
                    except Exception:
                        pass
                for k in ('contractSize', 'quanto_multiplier', 'multiplier', 'size', 'contract_size'):
                    v = info.get(k)
                    if v is not None:
                        try:
                            f = float(v)
                            if f > 0:
                                return f
                        except Exception:
                            continue
            return cs

        # helper to compute notional and attach as amount_
        def _compute_and_set_notional(leg, client):
            try:
                sym = _to_swap_symbol(getattr(leg, 'symbol', ''))
                try:
                    market = client.market(sym)
                except Exception:
                    market = None
                cs = _contract_size_from_market(market)
                entry = float(getattr(leg, 'entry_price', 0.0) or 0.0)
                contracts = float(getattr(leg, 'amount', 0.0) or 0.0)
                notional = round(max(0.0, contracts) * cs * max(0.0, entry), 2)
                setattr(leg, 'amount_', notional)
            except Exception:
                try:
                    setattr(leg, 'amount_', 0.0)
                except Exception:
                    pass

        for pos in self.fr_arbitrage_core.positions:
            # choose client by exchange for display
            long_client = bitget if pos.long_position.exchange == EXCHANGE.BITGET else gate
            short_client = bitget if pos.short_position.exchange == EXCHANGE.BITGET else gate
            _compute_and_set_notional(pos.long_position, long_client)
            _compute_and_set_notional(pos.short_position, short_client)

    def refresh_unreal_pnl(self):
        # Deprecated: no-op to keep compatibility if called somewhere
        return

    def get_core_positions(self):
        return self.fr_arbitrage_core.positions
