import threading
import time

from pydantic import BaseModel, Field

from Server.PositionCreator.PositionCreator import PositionCreator
from Server.ServiceManager.MicroserviceManager import MicroserviceManager
from Server.PositionView.PositionView import PositionView
from Core.Define import convert_exchange_to_name
from Core.Exchange.Exchange import ExchangeManager



class Position(BaseModel):
    symbol: str
    amount: float
    entry: float
    unrealpnl: float
    funding1: float
    funding2: float
    exchange1: str = "Bitget"
    exchange2: str = "Gate.io"

class FundingPoint(BaseModel):
    timestamp: int
    rate: float  # percentage, e.g. 0.01 means 1%

class FundingStats(BaseModel):
    symbol: str
    exchange1: str
    exchange2: str
    nextRate1: float | None = None
    nextRate2: float | None = None
    recent1: list[FundingPoint] = Field(default_factory=list)
    recent2: list[FundingPoint] = Field(default_factory=list)
    sumRate3d1: float | None = None
    sumRate7d1: float | None = None
    sumRate3d2: float | None = None
    sumRate7d2: float | None = None

class AppCore:
    def __init__(self):
        self.microservice_manager = MicroserviceManager()
        self.position_manager = PositionView()
        self.position_creator = PositionCreator()
        # Separate exchange manager for market data (funding rates)
        self.exchange_manager = ExchangeManager(self.position_manager.tracker.client.id.upper() if hasattr(self.position_manager.tracker.client, 'id') else None,
                                                self.position_manager.bitget_tracker.client.id.upper() if hasattr(self.position_manager.bitget_tracker.client, 'id') else None) if hasattr(self.position_manager, 'tracker') else ExchangeManager
        self.run()

    def get_microservices(self):
        services =  self.microservice_manager.get_microservices()
        return [ms.get_model() for ms in services]

    def start_microservice(self, service_id):
        return self.microservice_manager.start_microservice(service_id)

    def stop_microservice(self, service_id):
        return self.microservice_manager.stop_microservice(service_id)

    def main_loop(self):
        while True:
            for microservice in self.microservice_manager.get_microservices():
                microservice.ping()
            time.sleep(5)

    def run(self):
        main_thread = threading.Thread(target=self.main_loop)
        main_thread.start()

    def get_positions(self):
        self.position_manager.refresh()
        self.position_manager.refresh_unreal_pnl()
        position =  self.position_manager.get_core_positions()
        result = []
        for pos in position:
            result.append(Position(
                symbol=pos.long_position.symbol,
                amount=pos.long_position.amount_,
                entry=round(float(pos.long_position.entry_price), 2),
                unrealpnl=pos.unreal_pnl,
                funding1=round(float(getattr(pos.long_position, 'paid_funding', 0.0)), 2),
                funding2=round(float(getattr(pos.short_position, 'paid_funding', 0.0)), 2),
                exchange1=convert_exchange_to_name(pos.long_position.exchange),
                exchange2=convert_exchange_to_name(pos.short_position.exchange),
            ))

        return result

    def _to_bitget_symbol(self, internal_symbol: str) -> str:
        # internal like BTCUSDT -> BTC/USDT:USDT
        if internal_symbol.endswith('USDT') and '/' not in internal_symbol:
            base = internal_symbol[:-4]
            return f"{base}/USDT:USDT"
        return internal_symbol

    def _to_gate_symbol(self, internal_symbol: str) -> str:
        # Gate USDT-margined perpetuals use BASE/USDT:USDT in ccxt
        if internal_symbol.endswith('USDT') and '/' not in internal_symbol:
            base = internal_symbol[:-4]
            return f"{base}/USDT:USDT"
        # If already a pair without :USDT, append it to force swap contract
        if "/USDT" in internal_symbol and ":USDT" not in internal_symbol:
            return internal_symbol + ":USDT"
        return internal_symbol

    def _normalize_swap_symbol(self, symbol: str) -> str:
        """Return a swap contract symbol like BTC/USDT:USDT if not already normalized."""
        if '/' in symbol and ':USDT' in symbol:
            return symbol
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            return f"{base}/USDT:USDT"
        return symbol

    def get_funding_stats(self, quick: bool = False) -> list[FundingStats]:
        import ccxt
        import time as _time

        # Ensure positions are up-to-date
        self.position_manager.refresh()
        core_positions = self.position_manager.get_core_positions()

        # Prepare clients
        # Use fresh ccxt instances with proper options, to avoid shared state surprises
        bitget = ccxt.bitget({ 'options': { 'defaultType': 'swap' } })
        gate = ccxt.gateio({ 'options': { 'defaultType': 'swap' } })

        now_ms = int(_time.time() * 1000)
        ms_3d = 3 * 24 * 60 * 60 * 1000
        ms_7d = 7 * 24 * 60 * 60 * 1000

        def fetch_funding_for(exchange_name: str, internal_symbol: str):
            next_rate = None
            recent: list[FundingPoint] = []
            sum3 = None
            sum7 = None
            try:
                if exchange_name == 'bitget':
                    sym = self._to_bitget_symbol(internal_symbol)
                    fr = bitget.fetchFundingRate(sym)
                    next_rate = float(fr.get('fundingRate')) if fr and fr.get('fundingRate') is not None else None
                    if not quick:
                        try:
                            hist = bitget.fetchFundingRateHistory(sym, limit=10)
                            def _ts(it):
                                return int(it.get('timestamp') or it.get('datetime') or 0)
                            hist = sorted([h for h in hist if h.get('fundingRate') is not None], key=_ts)
                            for item in hist[-3:]:
                                ts = _ts(item)
                                r = float(item.get('fundingRate'))
                                if ts and r is not None:
                                    recent.append(FundingPoint(timestamp=ts, rate=r))
                        except Exception:
                            pass
                elif exchange_name == 'gate':
                    sym = self._to_gate_symbol(internal_symbol)
                    fr = gate.fetchFundingRate(sym)
                    next_rate = float(fr.get('fundingRate')) if fr and fr.get('fundingRate') is not None else None
                    if not quick:
                        try:
                            hist = gate.fetchFundingRateHistory(sym, limit=10)
                            def _tsg(it):
                                return int(it.get('timestamp') or it.get('datetime') or 0)
                            hist = sorted([h for h in hist if h.get('fundingRate') is not None], key=_tsg)
                            for item in hist[-3:]:
                                ts = _tsg(item)
                                r = float(item.get('fundingRate'))
                                if ts and r is not None:
                                    recent.append(FundingPoint(timestamp=ts, rate=r))
                        except Exception:
                            pass
                # compute sums for compatibility if we have recents
                if recent:
                    s3 = 0.0
                    s7 = 0.0
                    for p in recent:
                        if p.timestamp >= now_ms - ms_7d:
                            s7 += p.rate
                            if p.timestamp >= now_ms - ms_3d:
                                s3 += p.rate
                    sum3 = s3
                    sum7 = s7
            except Exception:
                pass
            return next_rate, recent, sum3, sum7

        # For each arbitrage position, fetch funding data for both exchanges
        output: list[FundingStats] = []
        for arb in core_positions:
            internal_symbol = arb.long_position.symbol
            ex1 = convert_exchange_to_name(arb.long_position.exchange)
            ex2 = convert_exchange_to_name(arb.short_position.exchange)
            stats = FundingStats(
                symbol=internal_symbol,
                exchange1=ex1,
                exchange2=ex2,
            )

            n1, r1, s3_1, s7_1 = fetch_funding_for(ex1, internal_symbol)
            n2, r2, s3_2, s7_2 = fetch_funding_for(ex2, internal_symbol)
            stats.nextRate1 = n1
            stats.recent1 = r1
            stats.sumRate3d1 = s3_1
            stats.sumRate7d1 = s7_1
            stats.nextRate2 = n2
            stats.recent2 = r2
            stats.sumRate3d2 = s3_2
            stats.sumRate7d2 = s7_2

            output.append(stats)

        return output

    def open_position(self, symbol, size):
        # Don't mutate symbol twice; estimate_position will normalize it
        result, e = self.estimate_position(symbol, size)
        if not result:
            print("Cannot open position:", symbol)
            return False, e
        # e may be a dict (new estimate result) or amount string (legacy)
        amount = None
        if isinstance(e, dict):
            try:
                # choose min contracts across both exchanges to be conservative
                c1 = float(e.get('bitget', {}).get('contracts') or 0)
                c2 = float(e.get('gate', {}).get('contracts') or 0)
                amount = str(max(0.0, min(c1, c2)))
            except Exception:
                amount = None
        else:
            amount = str(e)
        self.position_creator.open_position(self._normalize_swap_symbol(symbol), amount or "0")
        return True, e

    def estimate_position(self, symbol, size):
        symbol = self._normalize_swap_symbol(symbol)
        return self.position_creator.estimate_position(symbol, size)

    def open_position_hedge(self, symbol: str, long_exchange: str, long_contracts: float, short_exchange: str, short_contracts: float):
        # do not normalize twice; PositionCreator handles per-exchange symbols
        return self.position_creator.open_hedge_position(symbol, long_exchange, long_contracts, short_exchange, short_contracts)
