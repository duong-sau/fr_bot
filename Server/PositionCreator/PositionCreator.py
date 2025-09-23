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

    # Helpers to normalize symbols per exchange
    def _to_bitget_symbol(self, symbol: str) -> str:
        # Prefer swap form with ":USDT" suffix for bitget USDT-margined swaps
        if symbol.endswith(":USDT"):
            return symbol
        if "/" in symbol:
            base, quote = symbol.split("/")
            if quote.startswith("USDT"):
                return f"{base}/USDT:USDT"
        if symbol.endswith("USDT") and "/" not in symbol:
            base = symbol[:-4]
            return f"{base}/USDT:USDT"
        return symbol

    def _to_gate_symbol(self, symbol: str) -> str:
        # Gate USDT-margined perpetuals use "BASE/USDT:USDT" in ccxt for swap disambiguation
        if symbol.endswith(":USDT"):
            return symbol
        if "/" in symbol:
            base, quote = symbol.split("/")
            if quote.startswith("USDT"):
                return f"{base}/USDT:USDT"
        if symbol.endswith("USDT") and "/" not in symbol:
            base = symbol[:-4]
            return f"{base}/USDT:USDT"
        return symbol

    def _ensure_markets(self):
        try:
            if not getattr(self.bitget, 'markets', None):
                self.bitget.load_markets()
        except Exception:
            pass
        try:
            if not getattr(self.gate, 'markets', None):
                self.gate.load_markets()
        except Exception:
            pass

    def _extract_contract_size(self, market: dict) -> float:
        """Robustly extract contract size (base units per 1 contract) from a ccxt market."""
        if not market:
            return 1.0
        # Standardized field first
        cs = market.get('contractSize')
        if cs:
            try:
                return float(cs)
            except Exception:
                pass
        info = market.get('info') or {}
        # Common vendor fields
        for key in (
            'contractSize',             # sometimes nested in info
            'quanto_multiplier',        # Gate
            'multiplier',               # various
            'size',                     # bitget/gate variants
            'contract_size',
        ):
            val = info.get(key)
            if val is not None:
                try:
                    f = float(val)
                    if f > 0:
                        return f
                except Exception:
                    continue
        # As a last resort, 1.0 to avoid crash (but likely overestimates notional)
        return 1.0

    def _extract_amount_step(self, market: dict) -> float:
        """Extract minimum increment (step) for the amount (contracts)."""
        if not market:
            return 1.0
        # precision-based
        prec = (market.get('precision') or {}).get('amount')
        if prec is not None:
            try:
                f = float(prec)
                # If f is integer-like and small, interpret as number of decimals
                if abs(f - int(f)) < 1e-9 and 0 <= int(f) <= 10:
                    return float(10 ** (-int(f)))
                # If f is a positive fractional step already (<1), use as-is
                if 0 < f < 1:
                    return f
            except Exception:
                pass
        # limits-based
        try:
            lim_min = (((market.get('limits') or {}).get('amount') or {}).get('min'))
            if lim_min is not None:
                v = float(lim_min)
                if v > 0:
                    return v
        except Exception:
            pass
        # vendor info keys
        info = market.get('info') or {}
        for key in (
            'min_qty', 'minQuantity', 'min_amount', 'minAmount', 'minOrderQty', 'min_order_qty'
        ):
            val = info.get(key)
            if val is not None:
                try:
                    v = float(val)
                    if v > 0:
                        return v
                except Exception:
                    continue
        return 1.0

    def _quantize_to_step(self, value: float, step: float) -> float:
        if step <= 0:
            return float(value)
        # floor to nearest step
        q = math.floor(float(value) / step) * step
        # avoid negative zero due to float errors
        if abs(q) < 1e-12:
            q = 0.0
        # round to a sensible number of decimals based on step
        try:
            decimals = max(0, int(round(-math.log10(step))))
        except Exception:
            decimals = 8
        return round(q, decimals)

    def _common_step(self, s1: float, s2: float) -> float:
        """Return a step size that is a multiple of both s1 and s2.
        For typical decimal steps (powers of 10), the max works if it's a multiple; otherwise fall back to a conservative max.
        """
        try:
            s1 = float(s1 or 0)
            s2 = float(s2 or 0)
            if s1 <= 0 and s2 <= 0:
                return 1.0
            if s1 <= 0:
                return s2
            if s2 <= 0:
                return s1
            m = max(s1, s2)
            n = min(s1, s2)
            ratio = m / n
            nearest = round(ratio)
            if abs(ratio - nearest) < 1e-9:
                return m  # m is a multiple of n
            # Fallback: return m (more restrictive) to ensure we don't propose amounts not valid on the stricter exchange
            return m
        except Exception:
            return max(s1, s2) if (s1 or s2) else 1.0

    def _common_base_step(self, cs1: float, step1: float, cs2: float, step2: float) -> float:
        """Common base amount step (in base units), i.e., contractSize*amountStep per exchange reconciled.
        This returns a step that is representable on both exchanges. Uses the more restrictive step if not a clean multiple."""
        try:
            b1 = float(cs1) * float(step1)
            b2 = float(cs2) * float(step2)
            # Similar logic as _common_step but on base steps
            if b1 <= 0 and b2 <= 0:
                return 1.0
            if b1 <= 0:
                return b2
            if b2 <= 0:
                return b1
            m = max(b1, b2)
            n = min(b1, b2)
            ratio = m / n
            nearest = round(ratio)
            if abs(ratio - nearest) < 1e-9:
                return m
            # Fallback: return m (more restrictive) to ensure we don't propose amounts not valid on the stricter exchange
            return m
        except Exception:
            return max(cs1 * step1, cs2 * step2)

    def _try_float(self, v):
        try:
            if v is None:
                return None
            f = float(v)
            if not (f == f) or f == float('inf') or f == float('-inf'):
                return None
            return f
        except Exception:
            return None

    def _extract_open_interest_usdt(self, exchange, symbol: str, ticker: dict, price: float, contract_size: float):
        """Best-effort extraction of Open Interest in USDT.
        Priority:
        1) ticker.openInterestValue (already quote notional)
        2) ticker.openInterest (assumed contracts or base units) * price * contract_size
        3) vendor-specific info fields
        4) exchange.fetchOpenInterest if supported
        Returns float or None.
        """
        oi_usdt = None
        # 1) direct value from ticker
        if isinstance(ticker, dict):
            v = ticker.get('openInterestValue')
            v = self._try_float(v)
            if v is not None and v > 0:
                oi_usdt = v
            if oi_usdt is None:
                oi = self._try_float(ticker.get('openInterest'))
                if oi is not None and oi > 0:
                    # assume oi is in contracts; convert to USDT via price * contractSize
                    conv = self._try_float(price) and self._try_float(contract_size)
                    try:
                        oi_usdt = float(oi) * float(price) * float(contract_size)
                    except Exception:
                        oi_usdt = None
            if oi_usdt is None:
                info = ticker.get('info') or {}
                # common vendor info keys for OI notional
                for key in ('open_interest_value', 'openInterestValue', 'oiValue', 'holdVolValue'):
                    v2 = self._try_float(info.get(key))
                    if v2 is not None and v2 > 0:
                        oi_usdt = v2
                        break
                # common vendor info keys for OI amount (contracts/base)
                if oi_usdt is None:
                    for key in ('open_interest', 'openInterest', 'oi', 'holdVol'):
                        oi2 = self._try_float(info.get(key))
                        if oi2 is not None and oi2 > 0:
                            try:
                                oi_usdt = float(oi2) * float(price) * float(contract_size)
                                break
                            except Exception:
                                pass
        # 4) fetchOpenInterest
        if oi_usdt is None:
            try:
                if isinstance(getattr(exchange, 'has', None), dict) and exchange.has.get('fetchOpenInterest'):
                    data = exchange.fetchOpenInterest(symbol)
                    if isinstance(data, dict):
                        v = self._try_float(data.get('openInterestValue'))
                        if v is not None and v > 0:
                            oi_usdt = v
                        if oi_usdt is None:
                            oi = self._try_float(data.get('openInterest')) or self._try_float((data.get('info') or {}).get('open_interest'))
                            if oi is not None and oi > 0:
                                try:
                                    oi_usdt = float(oi) * float(price) * float(contract_size)
                                except Exception:
                                    oi_usdt = None
            except Exception:
                pass
        return oi_usdt

    def _bitget_open_interest_fallback(self, symbol_usdt_pair: str, price: float, contract_size: float):
        """Bitget vendor-specific open interest fallback using mix market endpoint.
        symbol_usdt_pair example: BTCUSDT
        Returns USDT notional or None.
        """
        try:
            method = getattr(self.bitget, 'publicMixGetMarketOpenInterest', None)
            if not callable(method):
                return None
            params = { 'symbol': symbol_usdt_pair, 'productType': 'USDT-FUTURES' }
            resp = method(params)
            data = None
            if isinstance(resp, dict):
                data = resp.get('data')
            if isinstance(data, list) and data:
                item = data[0] or {}
                # Try direct notional
                v = self._try_float(item.get('openInterestValue') or item.get('open_interest_value'))
                if v is not None and v > 0:
                    return v
                # Try contracts amount and convert
                oi = self._try_float(item.get('openInterest') or item.get('open_interest') or item.get('amount'))
                if oi is not None and oi > 0:
                    try:
                        return float(oi) * float(price) * float(contract_size)
                    except Exception:
                        return None
        except Exception:
            return None
        return None

    def _gate_open_interest_fallback(self, market_id: str, price: float, contract_size: float):
        """Gate.io vendor-specific open interest fallback using futures tickers endpoint with settle=usdt.
        market_id example: BTC_USDT
        Returns USDT notional or None.
        """
        try:
            method = getattr(self.gate, 'publicFuturesGetTickers', None)
            if not callable(method):
                return None
            resp = method({ 'settle': 'usdt', 'contract': market_id })
            rows = None
            if isinstance(resp, list):
                rows = resp
            elif isinstance(resp, dict):
                rows = resp.get('tickers') or resp.get('data') or []
            if rows:
                item = rows[0] or {}
                # Direct notional if present
                v = self._try_float(item.get('open_interest_value') or item.get('openInterestValue'))
                if v is not None and v > 0:
                    return v
                # Amount then convert
                oi = self._try_float(item.get('open_interest') or item.get('openInterest') or item.get('oi'))
                if oi is not None and oi > 0:
                    try:
                        return float(oi) * float(price) * float(contract_size)
                    except Exception:
                        return None
        except Exception:
            return None
        return None

    def estimate_position(self, symbol, size):
        try:
            # Normalize case first to match exchange market symbols
            symbol = (symbol or '').upper()
            # Normalize symbols for each exchange (force swap symbols)
            bg_symbol = self._to_bitget_symbol(symbol)
            gt_symbol = self._to_gate_symbol(symbol)

            # Ensure markets are loaded for contractSize lookup
            self._ensure_markets()

            # Get current price from Bitget and Gate exchanges
            # Use full ticker objects to inspect open interest fields
            bg_ticker = self.bitget.fetch_ticker(bg_symbol)
            gt_ticker = self.gate.fetch_ticker(gt_symbol)
            bitget_price = bg_ticker['last']
            gate_price = gt_ticker['last']

            # Load markets for the normalized symbols
            bg_market = None
            gt_market = None
            try:
                bg_market = self.bitget.market(bg_symbol)
            except Exception:
                pass
            try:
                gt_market = self.gate.market(gt_symbol)
            except Exception:
                pass

            # Extract accurate contract sizes and amount steps
            bg_contract_size = self._extract_contract_size(bg_market)
            gt_contract_size = self._extract_contract_size(gt_market)
            bg_step = self._extract_amount_step(bg_market)
            gt_step = self._extract_amount_step(gt_market)

            # Compute Open Interest (USDT) best-effort
            bg_oi_usdt = self._extract_open_interest_usdt(self.bitget, bg_symbol, bg_ticker, bitget_price, bg_contract_size)
            gt_oi_usdt = self._extract_open_interest_usdt(self.gate, gt_symbol, gt_ticker, gate_price, gt_contract_size)

            # Fallbacks via vendor-specific endpoints if still None
            if bg_oi_usdt is None:
                # Build BTCUSDT-like symbol from normalized input
                try:
                    base = symbol.split('/')[0].replace(':USDT', '') if '/' in symbol else symbol.replace('USDT', '')
                    pair = f"{base}USDT"
                except Exception:
                    pair = None
                if pair:
                    bg_oi_usdt = self._bitget_open_interest_fallback(pair, bitget_price, bg_contract_size)
            if gt_oi_usdt is None:
                try:
                    gt_market = self.gate.market(gt_symbol)
                    market_id = (gt_market or {}).get('id')
                except Exception:
                    market_id = None
                if market_id:
                    gt_oi_usdt = self._gate_open_interest_fallback(market_id, gate_price, gt_contract_size)

            # Calculate contract counts per side based on notional = size (1x)
            def calc_contracts(sz, px, cs, step):
                try:
                    raw = float(sz) / (float(px) * float(cs))
                    return self._quantize_to_step(raw, step)
                except Exception:
                    return 0.0

            contracts_bg_max = calc_contracts(size, bitget_price, bg_contract_size, bg_step)
            contracts_gt_max = calc_contracts(size, gate_price, gt_contract_size, gt_step)

            # Convert to base (contracts * contractSize)
            base_bg_max = float(contracts_bg_max) * float(bg_contract_size)
            base_gt_max = float(contracts_gt_max) * float(gt_contract_size)

            # Determine common base step and equal base amount
            common_base_step = self._common_base_step(bg_contract_size, bg_step, gt_contract_size, gt_step)
            # Max equal base we can do on both sides (respecting both budgets)
            equal_base = self._quantize_to_step(min(base_bg_max, base_gt_max), common_base_step)

            # Derive per-exchange contracts from equal_base (should align to steps due to common base step)
            contracts_bg_equal = self._quantize_to_step(equal_base / float(bg_contract_size), bg_step)
            contracts_gt_equal = self._quantize_to_step(equal_base / float(gt_contract_size), gt_step)

            # Compute minimal USDT for one min step per exchange and both (using common base step)
            min_usdt_bg_1 = float(bitget_price) * float(bg_contract_size)
            min_usdt_gt_1 = float(gate_price) * float(gt_contract_size)
            min_usdt_bg_step = float(bitget_price) * (float(bg_contract_size) * float(bg_step))
            min_usdt_gt_step = float(gate_price) * (float(gt_contract_size) * float(gt_step))
            min_usdt_both_equal_min_step = max(float(bitget_price) * common_base_step, float(gate_price) * common_base_step)

            result = {
                "symbol": symbol,
                "requestedSizeUSDT": float(size),
                "bitget": {
                    "exchange": "Bitget",
                    "symbol": bg_symbol,
                    "price": float(bitget_price),
                    "contractSize": float(bg_contract_size),
                    "amountStep": float(bg_step),
                    "contracts": float(contracts_bg_max),
                    "minUsdtFor1Contract": round(min_usdt_bg_1, 4),
                    "minUsdtForMinStep": round(min_usdt_bg_step, 6),
                    "openInterestUSDT": round(float(bg_oi_usdt), 2) if bg_oi_usdt is not None else None,
                },
                "gate": {
                    "exchange": "Gate.io",
                    "symbol": gt_symbol,
                    "price": float(gate_price),
                    "contractSize": float(gt_contract_size),
                    "amountStep": float(gt_step),
                    "contracts": float(contracts_gt_max),
                    "minUsdtFor1Contract": round(min_usdt_gt_1, 4),
                    "minUsdtForMinStep": round(min_usdt_gt_step, 6),
                    "openInterestUSDT": round(float(gt_oi_usdt), 2) if gt_oi_usdt is not None else None,
                },
                "equal": {
                    "baseStep": float(common_base_step),
                    "baseAmount": float(equal_base),
                    "bitgetContracts": float(contracts_bg_equal),
                    "gateContracts": float(contracts_gt_equal),
                },
                # Legacy fields
                "minUsdtForBoth": round(max(min_usdt_bg_1, min_usdt_gt_1), 4),
                # Updated to reflect equal-base minimal step cost across both sides
                "minUsdtForBothMinStep": round(min_usdt_both_equal_min_step, 6),
                "options": [
                    {
                        "key": "LONG_BITGET_SHORT_GATE",
                        "label": "Long Bitget / Short Gate (bằng lượng cơ sở)",
                        "long": {"exchange": "bitget", "contracts": float(contracts_bg_equal)},
                        "short": {"exchange": "gate", "contracts": float(contracts_gt_equal)}
                    },
                    {
                        "key": "LONG_GATE_SHORT_BITGET",
                        "label": "Long Gate / Short Bitget (bằng lượng cơ sở)",
                        "long": {"exchange": "gate", "contracts": float(contracts_gt_equal)},
                        "short": {"exchange": "bitget", "contracts": float(contracts_bg_equal)}
                    }
                ]
            }

            if equal_base <= 0:
                msg = (
                    f"Kích thước quá nhỏ. Tối thiểu để khớp 1 bước bằng nhau theo lượng cơ sở: "
                    f"Bitget {float(bitget_price)*common_base_step:.6f} USDT, Gate {float(gate_price)*common_base_step:.6f} USDT. "
                    f"Hãy nhập ≥ {min_usdt_both_equal_min_step:.6f} USDT để có thể mở đồng thời cả hai bên."
                )
                return False, msg

            # Compute rounded presentation for options (nearest hundred, drop decimals)
            # Option 1: primary Bitget
            bg_prim, gt_sec, _ = self._compute_primary_rounded_contracts(
                bg_contract_size, bg_step, gt_contract_size, gt_step, equal_base
            )
            # Option 2: primary Gate
            gt_prim, bg_sec, _ = self._compute_primary_rounded_contracts(
                gt_contract_size, gt_step, bg_contract_size, bg_step, equal_base
            )
            # Fallback to equal contracts if rounding fails
            if bg_prim <= 0 or gt_sec <= 0:
                bg_prim = int(math.floor(contracts_bg_equal))
                gt_sec = int(math.floor(contracts_gt_equal))
            if gt_prim <= 0 or bg_sec <= 0:
                gt_prim = int(math.floor(contracts_gt_equal))
                bg_sec = int(math.floor(contracts_bg_equal))

            # Override options with rounded integer contracts
            result["options"] = [
                {
                    "key": "LONG_BITGET_SHORT_GATE",
                    "label": "Long Bitget / Short Gate (bằng lượng cơ sở)",
                    "long": {"exchange": "bitget", "contracts": int(bg_prim)},
                    "short": {"exchange": "gate", "contracts": int(gt_sec)}
                },
                {
                    "key": "LONG_GATE_SHORT_BITGET",
                    "label": "Long Gate / Short Bitget (bằng lượng cơ sở)",
                    "long": {"exchange": "gate", "contracts": int(gt_prim)},
                    "short": {"exchange": "bitget", "contracts": int(bg_sec)}
                }
            ]

            return True, result
        except Exception as e:
            print(f"Error estimating position for {symbol}: {e}")
            return False, str(e)

    def _round_contracts_int_last2(self, x: float) -> int:
        """Round contracts by rounding last two digits of the integer part (to nearest hundred) and drop decimals.
        SAFE: If integer part < 50, keep integer (no hundreds rounding) to avoid zero."""
        if x is None:
            return 0
        xi = int(math.floor(float(x)))
        if xi < 50:
            return xi
        return int(math.floor((xi + 50) / 100.0) * 100)

    def _compute_primary_rounded_contracts(self,
                                           cs_primary: float,
                                           step_primary: float,
                                           cs_secondary: float,
                                           step_secondary: float,
                                           equal_base_max: float) -> tuple[int, int, float]:
        """Compute rounded contracts anchored on the primary leg:
        - Round primary contracts to nearest hundred (remove decimals), capped by equal_base_max.
        - Derive secondary contracts as integer (quantized to its step) from the same base target.
        - Return (primary_int, secondary_int, base_target).
        """
        # Capacity in contracts on primary from equal_base_max
        cap_primary = float(equal_base_max) / float(cs_primary) if cs_primary else 0.0
        if cap_primary <= 0:
            return 0, 0, 0.0
        # Round to nearest 100 and cap to capacity
        c_primary = self._round_contracts_int_last2(cap_primary)
        # if overshoot, step down by 100s until within capacity
        attempts = 0
        while c_primary > cap_primary and attempts < 50:
            c_primary = max(0, c_primary - 100)
            attempts += 1
        if c_primary <= 0:
            # fallback to integer capacity without hundreds rounding
            c_primary = int(math.floor(cap_primary))
            if c_primary <= 0:
                return 0, 0, 0.0
        base_target = float(c_primary) * float(cs_primary)
        # Secondary contracts from base_target
        c_secondary_float = base_target / float(cs_secondary) if cs_secondary else 0.0
        c_secondary = self._quantize_to_step(c_secondary_float, float(step_secondary))
        c_secondary = int(math.floor(c_secondary))
        if c_secondary <= 0:
            # reduce primary by 100 and retry
            attempts2 = 0
            while attempts2 < 50:
                c_primary = max(0, c_primary - 100)
                if c_primary <= 0:
                    return 0, 0, 0.0
                base_target = float(c_primary) * float(cs_primary)
                c_secondary_float = base_target / float(cs_secondary) if cs_secondary else 0.0
                c_secondary = self._quantize_to_step(c_secondary_float, float(step_secondary))
                c_secondary = int(math.floor(c_secondary))
                if c_secondary > 0:
                    break
                attempts2 += 1
            if c_secondary <= 0:
                return 0, 0, 0.0
        return int(c_primary), int(c_secondary), float(base_target)

    def open_hedge_position(self, symbol: str, long_exchange: str, long_contracts: float, short_exchange: str, short_contracts: float):
        try:
            # Normalize case first
            symbol = (symbol or '').upper()
            long_exchange = (long_exchange or '').lower()
            short_exchange = (short_exchange or '').lower()
            if long_exchange == short_exchange:
                raise ValueError("Long and short exchanges must be different")
            if long_contracts <= 0 or short_contracts <= 0:
                raise ValueError("Contracts must be positive for both legs")

            # Normalize symbols and load meta
            bg_symbol = self._to_bitget_symbol(symbol)
            gt_symbol = self._to_gate_symbol(symbol)
            self._ensure_markets()
            try:
                bg_market = self.bitget.market(bg_symbol)
            except Exception:
                bg_market = None
            try:
                gt_market = self.gate.market(gt_symbol)
            except Exception:
                gt_market = None

            bg_cs = self._extract_contract_size(bg_market)
            gt_cs = self._extract_contract_size(gt_market)
            bg_step = self._extract_amount_step(bg_market)
            gt_step = self._extract_amount_step(gt_market)

            # Compute provided base amounts and equalize by base units
            base_long = float(long_contracts) * float(bg_cs if long_exchange == 'bitget' else gt_cs)
            base_short = float(short_contracts) * float(bg_cs if short_exchange == 'bitget' else gt_cs)

            common_base_step = self._common_base_step(bg_cs, bg_step, gt_cs, gt_step)
            equal_base = self._quantize_to_step(min(base_long, base_short), common_base_step)
            if equal_base <= 0:
                raise ValueError("Contracts too small after equalizing base amount")

            if long_exchange == 'bitget':
                equal = long_contracts * bg_cs - short_contracts * gt_cs
                if equal != 0:
                    raise ValueError("Long and short contracts do not match in base amount")
                long_order = self.bitget.create_order(bg_symbol, 'market', 'buy', long_contracts, None, { 'reduceOnly': False })
                # print("Long order:", bg_symbol, 'market', 'buy', long_contracts, None, { 'reduceOnly': False })
            else:
                equal = long_contracts * gt_cs - short_contracts * bg_cs
                if equal != 0:
                    raise ValueError("Long and short contracts do not match in base amount")
                long_order = self.gate.create_order(gt_symbol, 'market', 'buy', long_contracts, None, { 'reduceOnly': False })
                # print("Long order:", gt_symbol, 'market', 'buy', long_contracts, None, { 'reduceOnly': False })
            try:
                if short_exchange == 'bitget':
                    short_order = self.bitget.create_order(bg_symbol, 'market', 'sell', short_contracts, None, { 'reduceOnly': False })
                    # print("Short order:", bg_symbol, 'market', 'sell', short_contracts, None, { 'reduceOnly': False })
                else:
                    short_order = self.gate.create_order(gt_symbol, 'market', 'sell', short_contracts, None, { 'reduceOnly': False })
                    # print("Short order:", gt_symbol, 'market', 'sell', long_contracts, None, { 'reduceOnly': False })
                return True, {
                    'message': 'Open hedge request executed (equal base amount with integer-hundreds rounding)',
                    'orders': [
                        { 'exchange': 'Bitget' if long_exchange=='bitget' else 'Gate.io', 'side': 'long', 'request': long_contracts, 'symbol': bg_symbol if long_exchange=='bitget' else gt_symbol, 'result': long_order },
                        { 'exchange': 'Bitget' if short_exchange=='bitget' else 'Gate.io', 'side': 'short', 'request': short_contracts, 'symbol': bg_symbol if short_exchange=='bitget' else gt_symbol, 'result': short_order },
                    ],
                    'equalBase': equal_base
                }
            except Exception as e2:
                # Attempt to revert long leg if short leg fails
                try:
                    if long_exchange == 'bitget':
                        self.bitget.create_order(bg_symbol, 'market', 'sell', long_contracts, None, { 'reduceOnly': True })
                    else:
                        self.gate.create_order(gt_symbol, 'market', 'sell', long_contracts, None, { 'reduceOnly': True })
                except Exception:
                    pass
                return False, { 'error': f"Second (short) leg failed: {e2}" }
        except Exception as e:
            return False, str(e)
