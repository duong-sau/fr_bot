# Hướng dẫn cài đặt fr_bot lên server Ubuntu (dành cho người chưa quen Linux/WSL)

Tài liệu này dành cho người **cài đặt lần đầu trên một máy chủ Ubuntu thật** (VD: EC2 Linux, VPS...).
Không cần biết WSL, không cần biết Docker/systemd chi tiết — chỉ cần SSH vào máy và copy-paste lệnh theo
thứ tự bên dưới.

> Không áp dụng cho WSL trên Windows: `install.sh` cần `systemd` để chạy Server dạng service — máy Windows/WSL
> thường không có, nên chỉ nên dùng script này trên **Ubuntu thật** (bao gồm EC2 Linux, VPS, máy vật lý).

---

## 1. Yêu cầu trước khi bắt đầu

- Một máy chủ **Ubuntu** (khuyến nghị 22.04/24.04), có thể SSH vào bằng user có quyền `sudo`.
- User đó nên tên là `ubuntu` (mặc định của script). Nếu dùng user khác, xem mục "Đổi đường dẫn mặc định"
  bên dưới.
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

### Cách 1 — máy đã có sẵn code (clone tay trước, ví dụ để lấy chính `install.sh`)

```bash
cd /home/ubuntu/fr_bot/code   # hoặc thư mục bất kỳ đã có install.sh
./install.sh
```

Nếu file chưa có quyền chạy:
```bash
chmod +x install.sh
./install.sh
```

### Cách 2 — máy trắng, chưa có gì cả

Chỉ cần tải riêng file `install.sh` (không cần clone cả repo trước) rồi chạy — script tự `git clone` code
vào đúng `/home/ubuntu/fr_bot/code` qua HTTPS (repo public, không cần SSH key hay đăng nhập gì cả):
```bash
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
7. Mặc định **bỏ qua** phần build/run Docker cho ADLControl/AssetControl (xem `SKIP_MICROSERVICES` bên dưới).

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
bitget/bitget_sub) cho từng sàn — gõ vào không hiện chữ trên màn hình (bảo mật), Enter bỏ trống để giữ nguyên
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

## 5. Các lệnh vận hành thường dùng sau khi đã cài

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

## 6. Đổi đường dẫn/tuỳ chọn mặc định (không bắt buộc)

Muốn đổi user, port, hay bật luôn Docker cho ADL/Asset khi cài, truyền biến môi trường trước khi chạy:

```bash
APP_PORT=9000 SKIP_MICROSERVICES=0 ./install.sh
```

Các biến hay dùng: `APP_ROOT` (mặc định `/home/ubuntu/fr_bot`), `APP_PORT` (mặc định `8000`),
`GIT_REF` (nhánh git, mặc định `master`), `SKIP_MICROSERVICES` (`1`=bỏ qua Docker, `0`=build/run luôn ADL+Asset+Discord).

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
