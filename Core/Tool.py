import json
import time

import requests

from Define import discord_config_path

current_step = 0

bar = ['→', '↘', '↓', '↙', '←', '↖', '↑', '↗']

def step(messages=["Running..."]):
    global current_step
    current_step += 1
    if current_step >= 8:
        current_step = 0

    clear_lines = "\033[K" * len(messages)  # Xóa tất cả các dòng cũ
    move_cursor_up = f"\033[{len(messages) + 1}A"  # Đưa con trỏ lên trên

    output = "\n".join(f"{msg}" for msg in messages) + f"\n{bar[current_step]}..."
    print(f"{clear_lines}\n{output}{move_cursor_up}\r", end='', flush=True)

def clear_console():
    """
    Clear the console output.
    """
    print("\033[2J\033[H", end='', flush=True)

def try_this(func, params, log_func, retries=5, delay=10):
    """
    Retry a function with specified parameters up to a number of retries.
    """
    log_func(f"Try {func.__name__}: {params}, retries: {retries}, delay: {delay} seconds")
    if params is None:
        params = {}
    for attempt in range(retries):
        try:
            return func(**params)
        except Exception as e:
            log_func(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    log_func("All attempts failed")
    raise Exception("All attempts failed")

def write_log(message, filename):
    """
    Write a log message to a file.
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(f"[{timestamp}] - {message}")
    with open(filename, 'a') as f:
        f.write(f"{timestamp} - {message}\n")
    # DONE

def check_config_empty_by_error(fields):
    for field in fields:
        if not field:
            raise ValueError(f"Missing configuration for {field}")
with open(discord_config_path, 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
webhook_url = config['discord'].get('webhook', '')
def push_notification(message):
    """
    Gửi thông báo đến Discord thông qua webhook.
    :param message: Nội dung thông báo
    """
    data = {
        "content": message
    }
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        return True
    else:
        return False

