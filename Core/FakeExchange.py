"""
Exchange giả dùng cho DRY_RUN mode (Define.DRY_RUN) — cho phép chạy AssetControl mà
không cần API/tiền thật.

Chỉ implement đúng phần bề mặt ccxt mà fr_ccxt.CCXTWrapper thực sự gọi (fetch_balance),
theo đúng kiểu duck-typing mà tests/test_fr_ccxt_wrapper.py::DummyExchange đã chứng minh
CCXTWrapper chấp nhận — không cần sửa gì CCXTWrapper để dùng class này.

Số dư giả seed qua biến môi trường DRY_RUN_BALANCE_<TÊN SÀN VIẾT HOA> (đơn vị USDT,
mặc định 1000), để có thể mô phỏng lệch số dư giữa 2 sàn và quan sát AssetControl có
kích hoạt quyết định transfer hay không (transfer thật sẽ KHÔNG được spawn ở DRY_RUN —
xem MainProcess/AssetControl/Main.py::AssetProcess.transfer).
"""
import os


class FakeExchange:
    id = "fake"

    def __init__(self, exchange_name: str, initial_usdt: float | None = None):
        self.exchange_name = exchange_name
        if initial_usdt is None:
            env_key = f"DRY_RUN_BALANCE_{exchange_name.upper()}"
            initial_usdt = float(os.getenv(env_key, "1000"))
        self.usdt_total = initial_usdt

    def fetch_balance(self, params=None):
        return {
            "info": {"dry_run": True, "exchange": self.exchange_name},
            "total": {"USDT": self.usdt_total},
            "free": {"USDT": self.usdt_total},
        }
