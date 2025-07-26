import sys
import time
import os
import requests
import json

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

if __name__ == '__main__':

    with open('_settings/binance_bitget_ini/Config.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
    webhook_url = config['discord'].get('webhook', '')
    server_url = config['alive_server'].get('url', '')
    service_name = config['alive_server'].get('name', '')

    sub_server_ok = True
    push_notification('start discord bot')

    if len(sys.argv) < 2:
        print("Usage: python3 DiscordServer.py <log_file>")
        sys.exit(1)
    log_file = sys.argv[1]
    last_size = 0
    if os.path.exists(log_file):
        last_size = os.path.getsize(log_file)
    else:
        last_size = 0
    while True:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(last_size)
                new_lines = f.readlines()
                last_size = f.tell()
                for line in new_lines:
                    if line.strip():
                        push_notification(line.strip())

        _sub_server_ok = True
        try:
            resp = requests.get(f"{server_url}", params={"name": service_name})
            if not resp.ok or not resp.text.strip():
                _sub_server_ok = False
        except Exception:
            _sub_server_ok = False

        if sub_server_ok  != _sub_server_ok:
            sub_server_ok = _sub_server_ok
            if sub_server_ok:
                push_notification('Alive server is back online')
            else:
                push_notification('Alive server is lost')

        time.sleep(5)