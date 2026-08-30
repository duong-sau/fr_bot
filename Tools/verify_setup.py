"""
CLI kiểm tra nhanh cấu hình trước khi bật ADLControl/AssetControl:
- Xác thực API key/secret/passphrase của exchange1/exchange2 (đọc qua Config.get_credentials,
  đúng dữ liệu mà process thật sẽ dùng) bằng một lệnh fetch_balance chỉ-đọc.
- Gửi một tin nhắn test tới Discord webhook đang cấu hình.

Không tạo lệnh, không chuyển tiền — chỉ đọc/kiểm tra.

Usage:
    python Tools/verify_setup.py
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

import Config
from Core.Define import convert_exchange_to_name
from Core.Tool import ensure_utf8_stdout
from Core.Verify import verify_exchange_credentials
from Define import exchange1, exchange2
from Notification.Discord import load_webhook, send_to_discord

ensure_utf8_stdout()


def check_exchanges() -> bool:
    ok = True
    try:
        creds = Config.get_credentials(exchange1, exchange2)
    except (ValueError, SystemExit) as e:
        print(f"[credentials] FAILED: could not load exchange_key config: {e}\n")
        return False
    for exchange in (exchange1, exchange2):
        name = convert_exchange_to_name(exchange)
        info = creds[name]
        print(f"[{name}] checking credentials...")
        passed, message = verify_exchange_credentials(
            name, info.get('api_key', ''), info.get('api_secret', ''), info.get('password')
        )
        print(f"[{name}] {'OK' if passed else 'FAILED'}: {message}\n")
        ok = ok and passed
    return ok


def check_discord() -> bool:
    print("[discord] sending test message...")
    webhook_url = load_webhook()
    session = requests.Session()
    sent = send_to_discord(session, webhook_url, "[verify_setup] fr_bot: webhook hoạt động bình thường.")
    print(f"[discord] {'OK' if sent else 'FAILED'}\n")
    return sent


def main():
    print("=== fr_bot setup verification ===\n")

    exchanges_ok = check_exchanges()
    discord_ok = check_discord()

    ok = exchanges_ok and discord_ok
    print("=== " + ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED") + " ===")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
