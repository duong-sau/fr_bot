import sys
import time
import os
import json
import requests
from typing import List, Tuple

from Define import discord_config_path, shared_log_path

MAX_DISCORD_MESSAGE = 1900  # chừa biên để không vượt 2000 ký tự
DEFAULT_INTERVAL = int(os.getenv("LOG_INTERVAL", "5"))


def load_webhook() -> str:
    try:
        with open(discord_config_path, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
        return config.get('discord', {}).get('webhook', '')
    except Exception as e:
        print(f"[WARN] Không đọc được webhook từ cấu hình: {e}")
        return ''


def send_to_discord(session: requests.Session, webhook_url: str, text: str) -> bool:
    if not webhook_url:
        print("[WARN] Chưa cấu hình webhook_url, bỏ qua gửi.")
        return False
    data = {"content": text}
    try:
        resp = session.post(webhook_url, json=data, timeout=10)
        if resp.status_code in (200, 201, 202, 204):
            return True
        print(f"[WARN] Gửi Discord thất bại: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        print(f"[WARN] Lỗi khi gửi Discord: {e}")
        return False


def chunk_lines(lines: List[str], limit: int = MAX_DISCORD_MESSAGE) -> List[str]:
    chunks = []
    buf = []
    buf_len = 0
    for line in lines:
        line = line.rstrip('\n')
        if not line:
            continue
        # +1 cho ký tự xuống dòng khi join
        add_len = len(line) + (1 if buf else 0)
        if buf_len + add_len > limit:
            if buf:
                chunks.append("\n".join(buf))
            buf = [line]
            buf_len = len(line)
        else:
            buf.append(line)
            buf_len += add_len
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def read_new_lines(log_file: str, last_size: int) -> Tuple[List[str], int]:
    # Phát hiện xoá/truncate: nếu size nhỏ hơn last_size, đọc lại từ đầu
    try:
        size_now = os.path.getsize(log_file)
    except FileNotFoundError:
        return [], last_size

    mode = 'r'
    new_lines: List[str] = []
    with open(log_file, mode, encoding='utf-8', errors='replace') as f:
        if size_now < last_size:
            # file bị truncate
            last_size = 0
        f.seek(last_size)
        new_lines = f.readlines()
        last_size = f.tell()
    return new_lines, last_size


def main():
    # Xác định log_file: ưu tiên argv[1], sau đó env LOG_FILE, cuối cùng shared_log_path
    log_file = None
    if len(sys.argv) >= 2:
        log_file = sys.argv[1]
    else:
        log_file = os.getenv("LOG_FILE", shared_log_path)

    webhook_url = load_webhook()
    session = requests.Session()

    # Lần đầu: nếu file tồn tại -> đọc từ cuối file (không spam log cũ)
    last_size = 0
    if os.path.exists(log_file):
        try:
            last_size = os.path.getsize(log_file)
        except Exception:
            last_size = 0

    # Thông báo khởi động (không bắt buộc)
    send_to_discord(session, webhook_url, f"Discord log relay started. Watching: {log_file}")

    interval = max(1, DEFAULT_INTERVAL)
    while True:
        try:
            if os.path.exists(log_file):
                new_lines, last_size = read_new_lines(log_file, last_size)
                if new_lines:
                    for chunk in chunk_lines(new_lines):
                        send_to_discord(session, webhook_url, chunk)
            else:
                # File tạm chưa có, đợi
                pass
        except Exception as e:
            print(f"[WARN] Lỗi vòng đọc log: {e}")
        time.sleep(interval)


if __name__ == '__main__':
    main()
