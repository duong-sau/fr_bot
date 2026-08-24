# Hướng dẫn cài đặt fr_bot lên server Ubuntu (dành cho người chưa quen Linux/WSL)

Tài liệu này dành cho người **cài đặt lần đầu trên một máy chủ Ubuntu thật** (VD: EC2 Linux, VPS...).
Không cần biết WSL, không cần biết Docker/systemd chi tiết — chỉ cần SSH vào máy và copy-paste lệnh theo
thứ tự bên dưới.

> Không áp dụng cho WSL trên Windows: `install.sh` cần `systemd` để chạy Server dạng service — máy Windows/WSL
> thường không có, nên chỉ nên dùng script này trên **Ubuntu thật** (bao gồm EC2 Linux, VPS, máy vật lý).

---

## 1. Yêu cầu trước khi bắt đầu

- Một máy chủ **Ubuntu** (khuyến nghị 22.04/24.04), SSH vào bằng đúng user tên `ubuntu` có quyền `sudo` (script
  dùng cố định đường dẫn `/home/ubuntu/fr_bot/...`, không đổi được qua user khác).
- Máy có kết nối Internet (để `apt-get` cài Python/git/Docker và `git clone` code từ GitHub).

---

## 2. Vị trí đặt code — KHÔNG tự chọn tuỳ ý

Toàn bộ code và cấu hình bắt buộc phải nằm ở một đường dẫn cố định, vì `Define.py` trong code đọc cứng
đường dẫn này (không phải thư mục bạn `git clone` vào):

```
/home/ubuntu/fr_bot/            <- gốc, gọi là "APP_ROOT"
/home/ubuntu/fr_bot/code/       <- code repo nằm ở đây (KHÔNG phải ~/fr_bot hay nơi khác)
/home/ubuntu/fr_bot/code/_settings/   <- toàn bộ file cấu hình (config.txt, key sàn, ...)
/home/ubuntu/fr_bot/logs/       <- log dùng chung giữa các service
/home/ubuntu/fr_bot/venv/       <- Python virtualenv
```

**Bạn không cần tự tạo các thư mục này hay tự `git clone` tay** — script `install.sh` ở bước 3 sẽ tự làm hết
(tạo thư mục, clone/pull code đúng chỗ, tạo venv, cài Python deps). Chỉ cần biết đường dẫn này để lỡ có lỗi thì
biết tìm file ở đâu.

---

## 3. Chạy install.sh

Áp dụng cho máy trắng, chưa có gì cả (kể cả code) — chỉ cần tải riêng file `install.sh` rồi chạy, script tự
`git clone` code vào đúng `/home/ubuntu/fr_bot/code` qua HTTPS (repo public, không cần SSH key hay đăng nhập
gì cả).

SSH vào server xong, đứng ở thư mục home của user (`cd ~`, thường là `/home/ubuntu`) rồi chạy — không quan
trọng tải `install.sh` vào đâu vì script tự copy code sang `/home/ubuntu/fr_bot/code`, nhưng nên đứng ở `~`
cho gọn, tránh lẫn với thư mục khác:

```bash
cd ~
curl -fsSL https://raw.githubusercontent.com/duong-sau/fr_bot/master/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

Trong lúc chạy, script sẽ hỏi `sudo` password (để cài package, tạo systemd service) — nhập password của user
đang SSH vào là được.

### install.sh làm gì

1. Cài git/python3/venv/pip nếu thiếu.
2. Tạo `/home/ubuntu/fr_bot/{code,logs,data,venv}`.
3. Clone hoặc pull code mới nhất từ GitHub vào `code/`.
4. Tạo virtualenv, cài `requirements.txt`.
5. Nếu chưa có `_settings/config.txt`, **tự tạo file cấu hình mặc định** (bitget/gate, API key để trống) —
   không còn báo lỗi dừng cài như trước nữa.
6. Cài Server thành **systemd service** tên `frbot-server.service`, chạy `uvicorn` ở `http://127.0.0.1:8000`
   (chỉ nghe trên localhost — muốn truy cập từ ngoài thì cần thêm reverse proxy, ngoài phạm vi tài liệu này).
7. Mặc định **bỏ qua** phần build/run Docker cho ADLControl/AssetControl — hai service này bật sau qua API
   `PUT /bot1api/microservices/{id}/start` (server tự `docker build`/`docker create` khi được gọi).

Cài xong sẽ thấy dòng `[DONE] Server: http://127.0.0.1:8000 ...` — nghĩa là Server đã chạy.

Kiểm tra nhanh:
```bash
curl http://127.0.0.1:8000/health
# {"status":"healthy"}
sudo systemctl status frbot-server.service
```

---

## 4. Set API key + chỉnh cấu hình bằng `config_menu.sh`

`install.sh` chỉ tạo **khung** cấu hình rỗng (API key để trống). Muốn nhập key thật của sàn (Bitget/Gate/...)
hoặc đổi cặp sàn, địa chỉ nạp/rút, webhook Discord..., dùng menu tương tác:

```bash
cd /home/ubuntu/fr_bot/code
./config_menu.sh
```

Nếu chưa có quyền chạy:
```bash
chmod +x config_menu.sh
./config_menu.sh
```

Menu hiện ra:
```
1. Khoi tao / tai tao file config mau con thieu
2. Xem toan bo config hien tai
3. Sua config.txt (exchange1 / exchange2 / ini folder)
4. Sua balance.json (max_diff_rate)
5. Sua transfer.json (dia chi nap/rut moi san)
6. Sua config.json (Discord webhook)
7. Sua server.json (danh sach microservices)
8. Sua exchange_key.json (API key, local fallback)
0. Thoat
```

Với việc setup API key: chọn **8**, script sẽ hỏi lần lượt `api_key`/`api_secret` (và `password` nếu là
bitget) cho từng sàn — gõ vào không hiện chữ trên màn hình (bảo mật), Enter bỏ trống để giữ nguyên
giá trị cũ.

Chạy nhanh không qua menu (dùng thẳng lệnh, tương đương mục 8):
```bash
python3 Tools/manage_keys.py set bitget --local
python3 Tools/manage_keys.py set gate --local
python3 Tools/manage_keys.py list --local   # xem lại key đã che bớt
```

> Lưu ý: `install.sh` dựng ADLControl/AssetControl mặc định **ở trạng thái tắt** (`SKIP_MICROSERVICES=1`).
> Chỉ cần set API key thật trước khi bật 2 service này qua API `PUT /bot1api/microservices/{id}/start`
> (Server FastAPI đã chạy sẵn từ bước 3 sẽ tự `docker build`/`docker create` khi được gọi).

---

## 5. Lấy API key sàn + điền chain/mạng/địa chỉ ví cho transfer.json

### 5.1. Tạo API key trên từng sàn

Mỗi sàn có trang quản lý API key riêng, tạo xong dán vào `config_menu.sh` mục **8** (hoặc
`Tools/manage_keys.py set <exchange> --local`) như hướng dẫn ở mục 4.

- **Bitget**: đăng nhập bitget.com → góc trên bên phải, avatar → **API Management** (Quản lý API) →
  **Create API Key**. Cần bật quyền:
  - `Read` + `Trade` cho **Futures** (bot đọc vị thế, đặt lệnh ADL).
  - `Withdraw` nếu muốn `AssetControl` tự động chuyển tiền giữa hai sàn (bỏ qua nếu chỉ chạy ADLControl).
  - Bitget bắt buộc đặt thêm một **Passphrase** lúc tạo key — đây chính là field `password` trong
    `exchange_key.json` (script `manage_keys.py` sẽ tự hỏi field này khi chọn `bitget`).
  - `api_key`/`api_secret`/passphrase chỉ hiển thị **một lần duy nhất** lúc tạo — copy lại ngay, mất thì phải
    tạo key mới.
- **Gate.io**: đăng nhập gate.io → avatar góc phải → **API Management** (Quản lý API Key) → **Create API
  Key**. Bật quyền `Futures` (Perpetual Futures – Trade) và `Wallet`/`Withdraw` nếu cần AssetControl tự
  transfer. Gate không cần passphrase, chỉ có `api_key`/`api_secret`.
- **Binance** (nếu dùng thay Bitget/Gate): API Management trong phần quản lý tài khoản, bật `Enable Futures`
  và `Enable Withdrawals` nếu cần transfer tự động. Cũng chỉ có `api_key`/`api_secret`, không có passphrase.

Khuyến nghị bật **IP whitelist** cho từng key, trỏ đúng IP public của server đang chạy `install.sh` — key bị
lộ cũng không dùng được từ nơi khác. Nếu server chưa có IP tĩnh (VD EC2 chưa gắn Elastic IP) thì tạm bỏ qua
whitelist, nhưng nhớ bật lại sau khi có IP cố định.

### 5.2. Điền chain/mạng + địa chỉ ví cho transfer.json (mục 5 trong config_menu.sh)

`transfer.json` là nơi khai báo **địa chỉ nạp tiền (USDT) trên từng sàn**, để `Transfer.py` tự rút từ sàn này
và nạp sang sàn kia khi `AssetControl` phát hiện lệch số dư. Mỗi sàn có 3 trường:

```json
{
  "bitget":  { "address": "0xabc...", "chain": "APT", "network": "APT" },
  "gate":    { "address": "0xdef...", "chain": "APT", "network": "APT" }
}
```

- **`address`** — địa chỉ ví nạp USDT của **tài khoản Spot/Funding trên sàn đó** (không phải ví cá nhân bên
  ngoài). Lấy tại trang **Deposit / Nạp tiền** của sàn, chọn coin `USDT`, chọn đúng mạng (network) muốn dùng,
  sàn sẽ hiện địa chỉ ví tương ứng — copy y nguyên.
- **`chain`/`network`** — tên mạng blockchain dùng để chuyển USDT giữa 2 sàn, phải là tên **ccxt/sàn đó chấp
  nhận** khi gọi rút tiền (`withdraw`) chứ không phải tên hiển thị tuỳ ý. Xem đúng tên tại trang Nạp/Rút tiền
  của sàn (VD Bitget hiện `APT(Aptos)`, Gate hiện `APT`) rồi điền y hệt.
- **Cực kỳ quan trọng**: `chain`/`network` khai báo cho sàn nhận (nơi bỏ tiền vào) phải là **cùng một mạng
  blockchain** với mạng mà sàn gửi rút tiền ra — rút sai mạng so với mạng sàn kia hỗ trợ nạp sẽ **mất tiền
  vĩnh viễn**, không sàn nào chịu trách nhiệm khôi phục. Nên chuyển thử một khoản nhỏ trước khi để bot tự động
  chạy transfer thật.
- Code hiện đang mặc định trừ thêm phí rút khi transfer trên mạng Aptos (xem
  `MainProcess/AssetControl/Transfer/Transfer.py`, hàm `transfer_spot_to_swap`) — nếu đổi sang mạng khác cần
  kiểm tra lại phí rút thực tế của mạng đó và sửa lại phần trừ phí trong code nếu cần.

Điền qua menu (khuyến nghị, không cần nhớ đúng tên field JSON):
```bash
./config_menu.sh   # chọn mục 5, nhập address/chain/network cho từng sàn
```

---

## 6. Các lệnh vận hành thường dùng sau khi đã cài

```bash
# Xem log server
sudo journalctl -u frbot-server.service -f

# Restart server sau khi đổi config/key
sudo systemctl restart frbot-server.service

# Cập nhật code lên bản mới nhất rồi cài lại (an toàn, không đụng _settings/ và venv/)
cd /home/ubuntu/fr_bot/code
./install.sh
```

`install.sh` chạy lại nhiều lần là an toàn (idempotent) — nó tự đồng bộ code về đúng bản mới nhất trên GitHub
(`git reset --hard`) và giữ nguyên `_settings/` (config, API key) cũng như `venv/` đã có sẵn.

---

## 7. Sự cố thường gặp

- **`sudo: a password is required`** — SSH vào bằng user có quyền sudo và nhập password khi được hỏi; không
  chạy script qua kênh không tương tác (ví dụ script tự động) nếu chưa cấu hình `sudo` không cần mật khẩu.
- **`System has not been booted with systemd as init system`** — máy đang chạy không phải Ubuntu thật (ví dụ
  container/WSL1 không bật systemd). Chạy `install.sh` trên đúng máy Ubuntu thật, không dùng WSL để test phần
  này.
- **Server chạy nhưng gọi API từ máy khác không được** — đúng như thiết kế, systemd service chỉ bind
  `127.0.0.1` (localhost). Cần thêm reverse proxy (nginx/caddy) nếu muốn truy cập từ ngoài.
- **Quên API key đã set gì** — `python3 Tools/manage_keys.py list --local` xem lại (giá trị bị che bớt, không
  lộ toàn bộ key).
