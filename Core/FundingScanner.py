# Core/FundingScanner.py
"""
Quét funding rate định kỳ, công khai (public ccxt endpoints, KHÔNG cần API key) trên
nhiều sàn, theo kiểu vòng tròn (round-robin): quét lần lượt từng sàn một rồi lặp lại ngay,
thay vì quét hết rồi ngủ một khoảng dài — để phát hiện chênh lệch funding mới càng nhanh
càng tốt.

Dùng để tìm "cặp funding ngon": với mỗi symbol xuất hiện trên >= 2 sàn, so sánh funding rate
giữa sàn cao nhất và sàn thấp nhất — chênh lệch (spread) càng lớn thì càng đáng để hedge
(long ở sàn funding thấp, short ở sàn funding cao) để ăn chênh lệch funding.

Không phụ thuộc AssetControl/ADLControl, không cần Config.get_credentials() — chạy độc lập
ngay khi Server khởi động.
"""
import itertools
import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import ccxt

from Core.Logger import LogService, LogTarget, log_error, log_info, log_warning

DEFAULT_EXCHANGES = ["binance", "bitget", "gate"]
DEFAULT_QUOTE = "USDT"
DEFAULT_INTER_EXCHANGE_DELAY_SEC = 1.5
DEFAULT_TOP_N = 20
DEFAULT_MIN_SPREAD_PCT = 0.0


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _iso(ts_ms: Any) -> Optional[str]:
    ts = _safe_float(ts_ms)
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _load_scanner_config() -> dict:
    """Đọc `_settings/funding_scanner.json` (tuỳ chọn) để override danh sách sàn/độ trễ.
    Không tồn tại/không đọc được thì dùng mặc định — tính năng này không được phép chặn
    Server khởi động vì thiếu file cấu hình.
    """
    try:
        import Define
        path = os.path.join(Define.root_path, "code/_settings", "funding_scanner.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


class FundingRateScanner:
    """Quét funding rate công khai theo vòng tròn và giữ snapshot mới nhất trong bộ nhớ."""

    def __init__(
        self,
        exchange_ids: Optional[List[str]] = None,
        quote: str = DEFAULT_QUOTE,
        inter_exchange_delay: float = DEFAULT_INTER_EXCHANGE_DELAY_SEC,
        clients: Optional[Dict[str, Any]] = None,
    ):
        cfg = _load_scanner_config()
        self.exchange_ids = exchange_ids or cfg.get("exchanges") or list(DEFAULT_EXCHANGES)
        self.quote = quote or cfg.get("quote") or DEFAULT_QUOTE
        self.inter_exchange_delay = float(cfg.get("inter_exchange_delay_sec", inter_exchange_delay))
        self._symbol_suffix = f"/{self.quote}:{self.quote}"

        self._clients: Dict[str, Any] = clients or {
            ex_id: self._build_public_client(ex_id) for ex_id in self.exchange_ids
        }

        self._lock = threading.Lock()
        self._rates: Dict[str, Dict[str, dict]] = {ex_id: {} for ex_id in self.exchange_ids}
        self._last_scan: Dict[str, Optional[str]] = {ex_id: None for ex_id in self.exchange_ids}
        self._errors: Dict[str, Optional[str]] = {ex_id: None for ex_id in self.exchange_ids}
        self._cycle_count = 0

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _build_public_client(exchange_id: str):
        ex_cls = getattr(ccxt, exchange_id, None)
        if ex_cls is None:
            raise ValueError(f"Exchange '{exchange_id}' not supported by ccxt in this environment")
        # Không truyền apiKey/secret: fetch_funding_rates là public endpoint trên cả 3 sàn.
        return ex_cls({"enableRateLimit": True, "options": {"defaultType": "swap"}})

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log_info(LogService.FUNDING, f"Funding scanner started for exchanges: {self.exchange_ids}")

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run_loop(self):
        while not self._stop_event.is_set():
            for ex_id in self.exchange_ids:
                if self._stop_event.is_set():
                    break
                self._scan_exchange(ex_id)
                self._stop_event.wait(self.inter_exchange_delay)
            self._cycle_count += 1

    def _scan_exchange(self, ex_id: str):
        client = self._clients.get(ex_id)
        try:
            raw = client.fetch_funding_rates()
            parsed: Dict[str, dict] = {}
            for symbol, info in (raw or {}).items():
                if not symbol.endswith(self._symbol_suffix):
                    continue
                rate = _safe_float(info.get("fundingRate"))
                if rate is None:
                    continue
                parsed[symbol] = {
                    "rate": rate,
                    "mark_price": _safe_float(info.get("markPrice")),
                    "next_funding_time": _iso(info.get("fundingTimestamp") or info.get("nextFundingTimestamp")),
                    "updated_at": _iso(info.get("timestamp")) or datetime.now(timezone.utc).isoformat(),
                }
            with self._lock:
                self._rates[ex_id] = parsed
                self._last_scan[ex_id] = datetime.now(timezone.utc).isoformat()
                self._errors[ex_id] = None
        except Exception as e:
            with self._lock:
                self._errors[ex_id] = str(e)
            log_warning(LogService.FUNDING, f"Failed to fetch funding rates from {ex_id}: {e}", target=LogTarget.SERVICE)

    def get_top_pairs(self, limit: int = DEFAULT_TOP_N, min_spread_pct: float = DEFAULT_MIN_SPREAD_PCT) -> List[dict]:
        with self._lock:
            snapshot = {ex_id: dict(rates) for ex_id, rates in self._rates.items()}

        symbols: Dict[str, Dict[str, dict]] = {}
        for ex_id, rates in snapshot.items():
            for symbol, info in rates.items():
                symbols.setdefault(symbol, {})[ex_id] = info

        pairs = []
        for symbol, by_exchange in symbols.items():
            if len(by_exchange) < 2:
                continue
            best = None
            for ex_a, ex_b in itertools.combinations(by_exchange.keys(), 2):
                info_a, info_b = by_exchange[ex_a], by_exchange[ex_b]
                if info_a["rate"] >= info_b["rate"]:
                    high_ex, high_info, low_ex, low_info = ex_a, info_a, ex_b, info_b
                else:
                    high_ex, high_info, low_ex, low_info = ex_b, info_b, ex_a, info_a
                spread = high_info["rate"] - low_info["rate"]
                if best is None or spread > best["spread"]:
                    best = {
                        "symbol": symbol,
                        "high_exchange": high_ex,
                        "high_rate": high_info["rate"],
                        "high_rate_pct": high_info["rate"] * 100,
                        "low_exchange": low_ex,
                        "low_rate": low_info["rate"],
                        "low_rate_pct": low_info["rate"] * 100,
                        "spread": spread,
                        "spread_pct": spread * 100,
                        "mark_price": high_info.get("mark_price") or low_info.get("mark_price"),
                        "updated_at": max(
                            filter(None, [high_info.get("updated_at"), low_info.get("updated_at")]),
                            default=None,
                        ),
                    }
            if best is not None and best["spread_pct"] >= min_spread_pct:
                pairs.append(best)

        pairs.sort(key=lambda p: p["spread_pct"], reverse=True)
        return pairs[:limit]

    def get_status(self) -> dict:
        with self._lock:
            return {
                "running": self._thread is not None and self._thread.is_alive(),
                "exchanges": list(self.exchange_ids),
                "cycle_count": self._cycle_count,
                "last_scan": dict(self._last_scan),
                "symbol_count": {ex_id: len(rates) for ex_id, rates in self._rates.items()},
                "errors": dict(self._errors),
            }
