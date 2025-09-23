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
        # internal like BTCUSDT -> BTC/USDT
        if internal_symbol.endswith('USDT') and '/' not in internal_symbol:
            base = internal_symbol[:-4]
            return f"{base}/USDT"
        return internal_symbol

    def _normalize_swap_symbol(self, symbol: str) -> str:
        """Return a swap contract symbol like BTC/USDT:USDT if not already normalized."""
        if '/' in symbol:
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

        # Build a set of unique symbols
        symbols = []
        for pos in core_positions:
            sym = pos.long_position.symbol
            if sym not in symbols:
                symbols.append(sym)

        # Prepare clients
        # Use fresh ccxt instances with proper options, to avoid shared state surprises
        bitget = ccxt.bitget({ 'options': { 'defaultType': 'swap' } })
        gate = ccxt.gateio({ 'options': { 'defaultType': 'swap' } })

        now_ms = int(_time.time() * 1000)
        ms_3d = 3 * 24 * 60 * 60 * 1000
        ms_7d = 7 * 24 * 60 * 60 * 1000
        since_7d = now_ms - ms_7d

        # For each arbitrage position, fetch funding data for both exchanges
        output: list[FundingStats] = []
        for arb in core_positions:
            internal_symbol = arb.long_position.symbol
            stats = FundingStats(
                symbol=internal_symbol,
                exchange1=convert_exchange_to_name(arb.long_position.exchange),
                exchange2=convert_exchange_to_name(arb.short_position.exchange),
            )

            # Bitget next funding rate and optionally history
            try:
                bg_symbol = self._to_bitget_symbol(internal_symbol)
                fr_bg = bitget.fetchFundingRate(bg_symbol)
                rate_bg = float(fr_bg.get('fundingRate')) if fr_bg and fr_bg.get('fundingRate') is not None else None
                stats.nextRate1 = rate_bg
                if not quick:
                    recent_bg = []
                    try:
                        hist_bg = bitget.fetchFundingRateHistory(bg_symbol, since=since_7d, limit=200)
                        for item in hist_bg[-12:]:  # last up to 12 entries (~2 days if 4h intervals), but we requested 7d
                            ts = int(item.get('timestamp') or item.get('datetime') or 0)
                            r = float(item.get('fundingRate')) if item.get('fundingRate') is not None else None
                            if ts and r is not None:
                                recent_bg.append(FundingPoint(timestamp=ts, rate=r))
                    except Exception:
                        pass
                    stats.recent1 = recent_bg
                    # Sums within 3d and 7d
                    sum3 = 0.0
                    sum7 = 0.0
                    for p in recent_bg:
                        if p.timestamp >= now_ms - ms_7d:
                            sum7 += p.rate
                            if p.timestamp >= now_ms - ms_3d:
                                sum3 += p.rate
                    stats.sumRate3d1 = sum3
                    stats.sumRate7d1 = sum7
            except Exception:
                pass

            # Gate next funding rate and optionally history
            try:
                gt_symbol = self._to_gate_symbol(internal_symbol)
                fr_gt = gate.fetchFundingRate(gt_symbol)
                rate_gt = float(fr_gt.get('fundingRate')) if fr_gt and fr_gt.get('fundingRate') is not None else None
                stats.nextRate2 = rate_gt
                if not quick:
                    recent_gt = []
                    try:
                        hist_gt = gate.fetchFundingRateHistory(gt_symbol, since=since_7d, limit=200)
                        for item in hist_gt[-12:]:
                            ts = int(item.get('timestamp') or item.get('datetime') or 0)
                            r = float(item.get('fundingRate')) if item.get('fundingRate') is not None else None
                            if ts and r is not None:
                                recent_gt.append(FundingPoint(timestamp=ts, rate=r))
                    except Exception:
                        pass
                    stats.recent2 = recent_gt
                    # Sums within 3d and 7d
                    sum3 = 0.0
                    sum7 = 0.0
                    for p in recent_gt:
                        if p.timestamp >= now_ms - ms_7d:
                            sum7 += p.rate
                            if p.timestamp >= now_ms - ms_3d:
                                sum3 += p.rate
                    stats.sumRate3d2 = sum3
                    stats.sumRate7d2 = sum7
            except Exception:
                pass

            output.append(stats)

        return output

    def open_position(self, symbol, size):
        # Don't mutate symbol twice; estimate_position will normalize it
        result, e = self.estimate_position(symbol, size)
        if not result:
            print("Cannot open position:", symbol)
            return False, e
        self.position_creator.open_position(self._normalize_swap_symbol(symbol), e)
        return True, e

    def estimate_position(self, symbol, size):
        symbol = self._normalize_swap_symbol(symbol)
        return self.position_creator.estimate_position(symbol, size)
