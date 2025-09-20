# FR Bot – Server (FastAPI) + ADL/Asset Microservices (Docker)

Dự án gồm một Server FastAPI quản lý và điều phối các microservice (ADLControl, AssetControl) chạy trong Docker. Log của các tiến trình được ghi ra một Docker named volume riêng để bền vững qua restart.

## Mục lục
- Tổng quan kiến trúc
- Yêu cầu hệ thống
- Cấu hình bắt buộc (_settings)
- Chạy Server (FastAPI) cục bộ
- Build & Run Docker cho ADL/Asset
- API của Server (FastAPI)
- Logging & Volume (frbot_logs)
- Các script tiện ích
- Troubleshooting (lỗi thường gặp)

---

## Tổng quan kiến trúc

Thành phần chính:
- Server FastAPI: `Server/App.py`
  - Cung cấp API quản lý microservice: liệt kê, start/stop, và một số API liên quan vị thế.
- ADLControl (Docker image: `adlprocess`): `MainProcess/ADLControl/`
  - Theo dõi vị thế giữa Gate/Bitget, tự cân đối/đóng chéo khi lệch.
- AssetControl (Docker image: `assetprocess`): `MainProcess/AssetControl/`
  - Theo dõi cân bằng tài sản giữa các sàn, tự động chuyển quỹ khi chênh lệch vượt ngưỡng cấu hình.
- (Tuỳ chọn) Discord log relay: `DiscordDockerfile` + `Discord.py`
  - Đọc shared log và gửi thông báo Discord (nếu cần triển khai).

Cấu trúc thư mục đáng chú ý:
- `_settings/` – cấu hình runtime (bắt buộc)
- `Server/` – mã nguồn FastAPI
- `MainProcess/ADLControl/` – mã nguồn ADL + Dockerfile
- `MainProcess/AssetControl/` – mã nguồn Asset + Dockerfile
- `Core/` – tiện ích chung (Tool, Exchange, Tracker, ...)

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
- `<ini>/exchange.json`, `<ini>/transfer.json`, `<ini>/balance.json`, `<ini>/tp_sl.json`
- `config.json` (Discord webhook, nếu dùng): `{ "discord": { "webhook": "..." } }`
- `server.json` (danh sách microservices hiển thị trên UI/API), ví dụ:
```json
{
  "microservices": [
    { "name": "ADLControl", "host": "localhost" },
    { "name": "AssetControl", "host": "localhost" }
  ]
}
```

Lưu ý: Trong container Docker, dự án tự ưu tiên đường dẫn `/app/code/_settings` (đã copy sẵn bởi Dockerfile). Ở môi trường máy chủ cũ, đường dẫn legacy là `/home/ubuntu/fr_bot/code/_settings` cũng được hỗ trợ (qua symlink và/hoặc logic autodetect).

---

## Chạy Server (FastAPI) cục bộ

Chạy trực tiếp file `Server/App.py`:
```bat
python Server\App.py
```
Server dùng Uvicorn chạy ở `http://127.0.0.1:8000/`.

Gỡ lỗi import: Dự án đã thêm `__init__.py` và tự động chỉnh `sys.path` trong `App.py` để chạy trực tiếp từ repo root.

---

## Build & Run Docker cho ADL/Asset

Mỗi tiến trình có Dockerfile riêng:
- ADLControl: `MainProcess/ADLControl/Dockerfile`
- AssetControl: `MainProcess/AssetControl/Dockerfile`

Build image:
```bat
docker build -f MainProcess\ADLControl\Dockerfile -t adlprocess .
docker build -f MainProcess\AssetControl\Dockerfile -t assetprocess .
```

Tạo container (manual) với volume log (khuyến nghị dùng API Start từ FastAPI – xem phần API):
```bat
REM Tạo volume log 1 lần (nếu chưa có)
docker volume create frbot_logs

REM ADL
docker create --name adlcontrol_container -v frbot_logs:/app/logs -v frbot_logs:/home/ubuntu/fr_bot/logs adlprocess

docker start adlcontrol_container

REM Asset
docker create --name assetcontrol_container -v frbot_logs:/app/logs -v frbot_logs:/home/ubuntu/fr_bot/logs assetprocess

docker start assetcontrol_container
```

Ghi chú:
- Hai mount point cùng trỏ đến `frbot_logs` để tương thích cả đường dẫn mới (`/app/logs`) và legacy (`/home/ubuntu/fr_bot/logs`).
- Các Dockerfile đã copy `_settings` vào image và tạo symlink phục vụ đường dẫn legacy.

---

## API của Server (FastAPI)
Cơ bản (prefix: `/bot1api`):
- `GET /bot1api/microservices` – Liệt kê microservices (id, name, status)
- `PUT /bot1api/microservices/{id}/start` – Start microservice theo id
  - Server sẽ tự tạo container nếu chưa tồn tại, gắn volume `frbot_logs` vào log paths.
  - Nếu container đã tồn tại nhưng thiếu volume, server sẽ stop + remove và tạo lại đúng chuẩn.
- `PUT /bot1api/microservices/{id}/stop` – Stop microservice theo id

Vị thế (nếu bật):
- `GET /bot1api/positions` – Lấy danh sách Position (Bitget/Gate)
- `POST /bot1api/positions/open` – Mở vị thế: body `{ "symbol": "...", "size": 123 }`
- `POST /bot1api/positions/estimate` – Ước tính mở vị thế: body `{ "symbol": "...", "size": 123 }`

---

## Logging & Volume (frbot_logs)
- Tất cả log được ghi vào trong container tại:
  - `/app/logs` (đường dẫn mới)
  - `/home/ubuntu/fr_bot/logs` (tương thích legacy)
- Các file/thư mục tiêu biểu:
  - `shared.log` – log dùng chung (để Discord relay đọc, nếu triển khai)
  - `asset/` – log AssetControl theo timestamp + `syslog.log`
  - `tunel/` – log quy trình chuyển tiền (Transfer)
  - `transfer_done.txt` – flag trạng thái chuyển tiền
- Khi ghi log, dự án tự tạo thư mục cha nếu chưa tồn tại (hữu ích khi volume rỗng).

Xem nội dung volume (ví dụ với container tạm):
```bat
REM Liệt kê trong volume
docker run --rm -v frbot_logs:/data alpine ls -R /data

REM Xem shared.log
docker run --rm -v frbot_logs:/data alpine sh -c "tail -n 200 /data/shared.log || true"
```

---

## Các script tiện ích
Một số script lịch sử vẫn tồn tại (`start_adl.sh`, `start_asset.sh`, `start_discord.sh`, `stop.sh`). Tuy nhiên, trong kiến trúc hiện tại:
- Khuyến nghị dùng API FastAPI để start/stop microservice (đảm bảo container kèm đúng volume log).
- Hoặc dùng các lệnh `docker build/create/start` như hướng dẫn ở trên.

---

## Troubleshooting (lỗi thường gặp)
- `Error response from daemon: No such container: adlcontrol_container`
  - Đã khắc phục: server khi `start` sẽ tự `docker create` (kèm volume) nếu container chưa tồn tại.
- `Setting file .../_settings/config.txt does not exist.`
  - Đảm bảo `_settings/config.txt` tồn tại. Trong image, Dockerfile đã copy `_settings`; code tự ưu tiên `/app/code/_settings`.
- `Permission denied` hoặc Docker không chạy
  - Bật Docker Desktop; kiểm tra `docker ps` chạy được.
- `404 Microservice not found` khi gọi API start/stop
  - Sai `id` microservice; hãy `GET /bot1api/microservices` để lấy đúng id hiện tại.
- Không thấy log mới
  - Kiểm tra container còn `Up`; kiểm tra volume `frbot_logs` có file/đường dẫn như trên; đảm bảo không mount sai volume.

---

## Ghi chú phát triển
- `Server/App.py` đã tự chèn sys.path để chạy trực tiếp từ repo.
- `Core/Tool.write_log` tự tạo thư mục log nếu chưa có (tương thích volume rỗng).
- `Define.py` tự động chọn `root_path` phù hợp (Windows vs Docker) và gom lưu log dưới `root_path/logs`.
- `MicroserviceManager.py` khi start sẽ:
  - Tự tạo container nếu thiếu, gắn volume `frbot_logs` cả vào `/app/logs` và đường dẫn legacy.
  - Nếu container đã có nhưng thiếu volume log, sẽ tự stop + remove và tạo lại.

---

## License
Internal project. Vui lòng không phân phối khi chưa có sự cho phép.
