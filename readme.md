# FR Bot – Server (FastAPI) + ADL/Asset Microservices (Docker)

Dự án gồm một Server FastAPI quản lý và điều phối các microservice (ADLControl, AssetControl, Discord relay)
chạy trong Docker. Các process không giao tiếp qua RPC mà phối hợp qua filesystem dùng chung (log, file trạng
thái transfer).

## Mục lục
- Tổng quan kiến trúc
- Yêu cầu hệ thống
- Cấu hình bắt buộc (_settings)
- ⚠️ Đường dẫn root_path (rất hay gây lỗi khi setup mới)
- Chạy Server (FastAPI) cục bộ
- Build & Run Docker cho ADL/Asset/Discord
- API của Server (FastAPI)
- Logging (shared.log / discord_simple.log / syslog.log)
- Trạng thái transfer liên-process
- Credentials (AWS Secrets Manager)
- Các script tiện ích
- Troubleshooting (lỗi thường gặp)

---

## Tổng quan kiến trúc

Thành phần chính:
- **Server FastAPI**: `Server/App.py` (+ `Server/AppCore.py`, `Server/ServiceManager/MicroserviceManager.py`)
  - Cung cấp API quản lý microservice: liệt kê, start/stop (thao tác trực tiếp qua Docker CLI bằng
    `subprocess`).
- **ADLControl** (Docker image: `adlprocess`): `MainProcess/ADLControl/`
  - Theo dõi vị thế giữa Bitget/Gate qua websocket (`ccxt.pro`), tự đóng bớt phần lệch khi hai sàn không còn
    khớp size (auto-deleverage).
- **AssetControl** (Docker image: `assetprocess`): `MainProcess/AssetControl/`
  - Poll số dư futures giữa hai sàn (qua `fr_ccxt.CCXTWrapper`), khi lệch quá `max_diff_rate` sẽ spawn
    `MainProcess/AssetControl/Transfer/Transfer.py` như một subprocess riêng để chuyển quỹ.
- **Transfer** (`MainProcess/AssetControl/Transfer/Transfer.py`): script chạy một lần (không phải service dài
  hạn), do AssetControl gọi. Vì hầu hết sàn không hỗ trợ chuyển thẳng futures↔futures giữa hai sàn khác nhau,
  script đi qua chuỗi swap → spot → withdraw → deposit → spot → swap.
- **Discord log relay**: `Notification/Discord.py` (Docker image: `discord_shared_image`, build từ
  `Notification/Dockerfile`)
  - Tail file `logs/discord_simple.log` (hoặc file chỉ định qua `LOG_FILE`) mỗi `LOG_INTERVAL` giây (mặc định
    5s) và forward nội dung mới lên Discord qua webhook.
- **Core/**: tiện ích dùng chung (`Define.py`, `Tool.py`, `Logger.py`, `secret.py`).
- **fr_ccxt/**: wrapper mỏng quanh `ccxt` (`CCXTWrapper`), chuẩn hoá balance futures về một shape chung.

Cấu trúc thư mục đáng chú ý:
- `_settings/` – cấu hình runtime (bắt buộc, nằm ngoài repo, xem phần root_path bên dưới)
- `Server/` – mã nguồn FastAPI
- `MainProcess/ADLControl/` – mã nguồn ADL + Dockerfile
- `MainProcess/AssetControl/` – mã nguồn Asset (+ `Transfer/`) + Dockerfile
- `Notification/` – Discord log relay + Dockerfile
- `Core/` – tiện ích chung
- `fr_ccxt/` – wrapper ccxt cho balance futures
- `tests/` – unittest, hiện chỉ cover `fr_ccxt`

Lưu ý: `Core/Exchange/Exchange.py` còn tồn tại trong repo nhưng không còn được import ở đâu — là code cũ
sót lại sau lần refactor sang `CCXTWrapper`, có thể bỏ qua khi đọc code.

---

## Yêu cầu hệ thống
- Python 3.11
- pip và virtualenv (khuyến nghị)
- Docker Desktop (Windows) hoặc Docker Engine (Linux)
- Quyền chạy Docker (đã bật Docker Desktop)

Cài dependencies Python (khi chạy Server cục bộ):
```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

---

## Cấu hình bắt buộc (_settings)

Thư mục `_settings/` chứa:
- `config.txt` (3 dòng):
  1. exchange1 (binance|bitget|bitget_sub|gate)
  2. exchange2 (binance|bitget|bitget_sub|gate)
  3. tên thư mục cấu hình INI (vd: `1_bitget_gate_ini`)
- `<ini>/exchange.json` — không còn dùng nữa (credentials hiện lấy từ AWS Secrets Manager, xem mục
  "Credentials" bên dưới); có thể vẫn tồn tại trên máy cũ nhưng code không đọc nữa.
- `<ini>/transfer.json` – địa chỉ/chain/network nạp tiền theo từng sàn, dùng bởi `Transfer.py`.
- `<ini>/balance.json` – `max_diff_rate` (đơn vị %) để AssetControl quyết định khi nào cần transfer.
- `<ini>/tp_sl.json` – được `Define.py` trỏ đường dẫn sẵn nhưng **hiện chưa có service nào đọc/dùng file
  này** (không có `MainProcess/TPSLControl`); coi như cấu hình dự phòng cho tính năng chưa triển khai.
- `config.json` (Discord webhook): `{ "discord": { "webhook": "..." } }`
- `server.json` (danh sách microservices hiển thị/điều khiển qua API), ví dụ:
```json
{
  "microservices": [
    { "name": "ADLControl", "host": "localhost" },
    { "name": "AssetControl", "host": "localhost" },
    { "name": "Discord", "host": "localhost" }
  ]
}
```
  `name` (không phân biệt hoa/thường) chỉ được nhận 1 trong 3 giá trị: `adlcontrol`, `assetcontrol`,
  `discord` — giá trị khác sẽ làm `MicroserviceManager` raise lỗi lúc khởi động Server.

---

## ⚠️ Đường dẫn root_path (rất hay gây lỗi khi setup mới)

`Define.py` không dùng thư mục checkout của git làm gốc. Nó tự chọn `root_path` cố định theo OS:

```python
if os.name == "nt":
    root_path = "C:\\job\\dim\\fr_bot\\"
else:
    root_path = "/home/ubuntu/fr_bot"
```

Tất cả đường dẫn `_settings`, log đều tính từ `root_path`, cụ thể là `root_path/code/_settings/...` và
`root_path/logs/...`. Nghĩa là:
- Trên Windows, dù bạn checkout repo ở đâu, `_settings/config.txt` **phải** đặt tại
  `C:\job\dim\fr_bot\code\_settings\config.txt`, nếu không `Define.py` sẽ raise
  `FileNotFoundError` ngay khi import.
- Trên Linux, tương tự phải đặt tại `/home/ubuntu/fr_bot/code/_settings/config.txt`.
- Trong Docker, các Dockerfile đã `COPY . /home/ubuntu/fr_bot/code` và tạo symlink `/app/code` →
  `/home/ubuntu/fr_bot/code`, `/app/logs` → `/home/ubuntu/fr_bot/logs`, nên cả đường dẫn mới lẫn legacy đều
  hoạt động bên trong container.

---

## Chạy Server (FastAPI) cục bộ

Chạy trực tiếp file `Server/App.py`:
```bat
python Server\App.py
```
Server dùng Uvicorn chạy ở `http://0.0.0.0:8000/` theo mặc định (đổi qua biến môi trường `UVICORN_HOST`,
`UVICORN_PORT`; có thể bật HTTPS qua `UVICORN_SSL_CERTFILE`/`UVICORN_SSL_KEYFILE`).

Gỡ lỗi import: Dự án đã thêm `__init__.py` và tự động chỉnh `sys.path` trong `App.py` để chạy trực tiếp từ
repo root. Trước khi chạy, nhớ đảm bảo `_settings/config.txt` đã có ở đúng `root_path` (xem mục trên).

---

## Build & Run Docker cho ADL/Asset/Discord

Mỗi tiến trình có Dockerfile riêng, build context là **repo root**:
- ADLControl: `MainProcess/ADLControl/Dockerfile`
- AssetControl: `MainProcess/AssetControl/Dockerfile`
- Discord relay: `Notification/Dockerfile`

Build image:
```bat
docker build -f MainProcess\ADLControl\Dockerfile -t adlprocess .
docker build -f MainProcess\AssetControl\Dockerfile -t assetprocess .
docker build -f Notification\Dockerfile -t discord_shared_image .
```

Khuyến nghị dùng API `PUT /bot1api/microservices/{id}/start` để tạo/khởi động container — nó tự lo đúng
volume mount và tự dựng lại container nếu thiếu mount (xem `MicroserviceManager.py`). Nếu muốn tạo thủ công,
container cần bind-mount **thư mục log/settings thật trên host** (không phải Docker named volume) vào cả
đường dẫn mới lẫn legacy để tương thích:
```bat
docker create --name adlcontrol_container ^
  -v /home/ubuntu/fr_bot/logs:/home/ubuntu/fr_bot/logs ^
  -v /home/ubuntu/fr_bot/logs:/app/logs ^
  -v /home/ubuntu/fr_bot/code/_settings:/home/ubuntu/fr_bot/code/_settings ^
  adlprocess

docker start adlcontrol_container
```
(Tương tự cho `assetcontrol_container` → image `assetprocess`, và `discord_shared_container` → image
`discord_shared_image`.)

---

## API của Server (FastAPI)
Prefix: `/bot1api`:
- `GET /bot1api/microservices` – Liệt kê microservices (id, name, status)
- `PUT /bot1api/microservices/{id}/start` – Start microservice theo id (tự tạo container nếu chưa có, tự vá
  lại mount nếu thiếu)
- `PUT /bot1api/microservices/{id}/stop` – Stop microservice theo id
- `GET /health` – health check đơn giản, trả `{"status": "healthy"}`

Server hiện **không** có API vị thế (`/positions`, `/positions/open`, `/positions/estimate`) — các phiên bản
readme cũ có nhắc tới nhưng những route này không tồn tại trong `Server/App.py` hiện tại.

---

## Logging (shared.log / discord_simple.log / syslog.log)

Logging tập trung qua `Core/Logger.py` (`log_info/log_warning/log_error/log_debug(LogService, message,
target=...)`), mỗi service (`ASSET`, `ADL`, `TUNEL`, `TP_SL`, `SERVER`) có thể ghi vào tối đa 3 nơi tuỳ
`target`:
- `logs/shared.log` – log đầy đủ level, dùng chung cho mọi service (trừ khi target khác `SHARED`/`ALL`)
- `logs/discord_simple.log` – chỉ log từ INFO trở lên, dùng cho Discord relay đọc (service `TUNEL` không ghi
  vào file này)
- `logs/<service>/syslog.log` – log riêng từng service (vd `logs/asset/syslog.log`)

Không cần tạo thư mục trước — `Logger.py`/`Tool.write_log` tự `os.makedirs` khi ghi lần đầu, kể cả khi volume
đang trống.

Xem log khi chạy trong Docker (ví dụ container tạm, đường dẫn host thật):
```bat
docker exec -it adlcontrol_container tail -n 200 /app/logs/shared.log
```

---

## Trạng thái transfer liên-process

AssetControl và Transfer.py không gọi nhau qua RPC — chúng đọc/ghi 2 file trạng thái dưới `logs/`:
- `transfer_done.txt` – file text kiểu cũ: dòng 1 là `WAIT`/`OK`/`ERROR`, dòng 2 (khi `WAIT`) là số tiền,
  dòng 3 là `from->to`.
- `transfer_status.json` – cùng thông tin ở dạng JSON, ghi atomic (`*.tmp` rồi `os.replace`) để container
  khác đọc được trạng thái nhất quán.

---

## Credentials (AWS Secrets Manager)

Có **hai** đường load credentials khác nhau trong repo, không nên coi là tương đương:
- `Config.get_credentials()` (dùng bởi ADLControl và `Transfer.py`) — đọc secret **`exchange_key`** ở region
  **`ap-southeast-1`**. Nếu không đọc được secret, process sẽ `sys.exit(1)` (không có fallback file JSON local
  nữa).
- `Core/secret.py:get_secret()` (dùng bởi `AssetControl/Main.py`) — đọc secret **`bot1_exchange_key`** ở
  region **`ap-southeast-2`**.

Khi cập nhật/luân chuyển API key, nhớ cập nhật **cả hai** secret ở đúng region tương ứng, nếu không AssetControl
và ADLControl sẽ dùng key khác nhau (hoặc một bên lỗi vì thiếu key).

---

## Các script tiện ích
- `install.sh` – cài đặt one-shot trên Ubuntu: dựng systemd service chạy `uvicorn Server.App:app`, tuỳ chọn
  build/run Docker cho ADL/Asset/Discord (mặc định `SKIP_MICROSERVICES=1`, bỏ qua phần Docker).
- `rebuild_docker.sh` – rebuild lại 3 image (ADL/Asset/Discord) và tạo lại container, dùng **host bind mount**
  cho log/settings (đúng với cách `MicroserviceManager.py` mount).

Một số script lịch sử khác (`start_adl.sh`, `start_asset.sh`, ...) nếu còn sót trên máy chủ cũ không còn được
bảo trì — ưu tiên dùng API FastAPI hoặc 2 script trên.

---

## Troubleshooting (lỗi thường gặp)
- `FileNotFoundError: Setting file .../_settings/config.txt does not exist.`
  - Kiểm tra đúng `root_path` cho OS đang chạy (xem mục "Đường dẫn root_path" ở trên) — lỗi phổ biến nhất khi
    setup máy mới hoặc chạy local trên Windows.
- `Error response from daemon: No such container: adlcontrol_container`
  - Không cần lo: khi gọi API `start`, server sẽ tự `docker create` (kèm đúng mount) nếu container chưa tồn
    tại.
- `Permission denied` hoặc Docker không chạy
  - Bật Docker Desktop; kiểm tra `docker ps` chạy được.
- `404 Microservice not found` khi gọi API start/stop
  - Sai `id` microservice; hãy `GET /bot1api/microservices` để lấy đúng id hiện tại (id là UUID sinh ngẫu
    nhiên mỗi lần Server khởi động, không cố định giữa các lần chạy).
- Không thấy log mới
  - Kiểm tra container còn `Up`; kiểm tra đúng thư mục host đang bind-mount (không phải Docker named volume
    nữa) có dữ liệu.

---

## License
Internal project. Vui lòng không phân phối khi chưa có sự cho phép.
