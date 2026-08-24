"""
CLI để xem/cập nhật exchange API key trong AWS Secrets Manager (secret `exchange_key`,
region `ap-southeast-1`) mà không phải sửa tay JSON trên AWS Console.

Dùng --local để thao tác trên file local (<root_path>/code/_settings/exchange_key.json)
thay vì AWS — đây là nguồn fallback mà Config.get_credentials() đọc khi không kết nối
được AWS Secrets Manager. Tiện cho chạy/test local không có AWS credentials.

Usage:
    python Tools/manage_keys.py list
    python Tools/manage_keys.py set bitget
    python Tools/manage_keys.py set gate --restart

    python Tools/manage_keys.py list --local
    python Tools/manage_keys.py set bitget --local
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from getpass import getpass

SECRET_NAME = "exchange_key"
REGION = "ap-southeast-1"

# Cùng công thức root_path với Define.py, để trỏ đúng file mà Config.py đọc làm fallback.
if os.name == "nt":
    _ROOT_PATH = "C:\\job\\dim\\fr_bot\\"
else:
    _ROOT_PATH = "/home/ubuntu/fr_bot"
LOCAL_KEY_FILE = os.path.join(_ROOT_PATH, "code", "_settings", "exchange_key.json")

EXCHANGE_FIELDS = {
    "binance": ["api_key", "api_secret"],
    "bitget": ["api_key", "api_secret", "password"],
    "gate": ["api_key", "api_secret"],
}

RESTART_CONTAINERS = ["adlcontrol_container", "assetcontrol_container"]


def get_client():
    return boto3.client("secretsmanager", region_name=REGION)


def fetch_secret(client):
    resp = client.get_secret_value(SecretId=SECRET_NAME)
    return json.loads(resp["SecretString"])


def put_secret(client, data):
    client.put_secret_value(SecretId=SECRET_NAME, SecretString=json.dumps(data, indent=2))


def fetch_local():
    if not os.path.exists(LOCAL_KEY_FILE):
        return {}
    with open(LOCAL_KEY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def put_local(data):
    os.makedirs(os.path.dirname(LOCAL_KEY_FILE), exist_ok=True)
    with open(LOCAL_KEY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def mask(value):
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return value[:2] + "*" * max(len(value) - 2, 0)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def cmd_list(args):
    if args.local:
        data = fetch_local()
        print(f"(reading from local file: {LOCAL_KEY_FILE})")
    else:
        client = get_client()
        data = fetch_secret(client)
    for exchange, fields in EXCHANGE_FIELDS.items():
        block = data.get(exchange, {})
        print(f"[{exchange}]")
        for field in fields:
            print(f"  {field}: {mask(block.get(field, ''))}")


def cmd_set(args):
    exchange = args.exchange
    if exchange not in EXCHANGE_FIELDS:
        print(f"Unknown exchange '{exchange}'. Must be one of: {', '.join(EXCHANGE_FIELDS)}", file=sys.stderr)
        sys.exit(1)

    client = None if args.local else get_client()
    data = fetch_local() if args.local else fetch_secret(client)
    block = data.get(exchange, {})

    print(f"Setting credentials for '{exchange}'. Leave blank to keep the current value.")
    for field in EXCHANGE_FIELDS[exchange]:
        current = block.get(field, "")
        prompt = f"  {field} [{mask(current)}]: "
        entered = getpass(prompt)
        if entered:
            block[field] = entered
    data[exchange] = block

    if args.local:
        put_local(data)
        print(f"Updated '{exchange}' in local file '{LOCAL_KEY_FILE}'.")
    else:
        put_secret(client, data)
        print(f"Updated '{exchange}' in secret '{SECRET_NAME}' ({REGION}).")
    print(
        "Credentials are only read once at process startup — restart the affected "
        f"container(s) ({', '.join(RESTART_CONTAINERS)}) to pick up the new key."
    )

    if args.restart:
        for container in RESTART_CONTAINERS:
            result = subprocess.run(["docker", "restart", container], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Restarted {container}.")
            else:
                print(f"Failed to restart {container}: {result.stderr.strip()}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Manage exchange API keys in AWS Secrets Manager.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Show masked credentials for every exchange.")
    list_parser.add_argument(
        "--local", action="store_true",
        help=f"Read from the local fallback file ({LOCAL_KEY_FILE}) instead of AWS Secrets Manager.",
    )

    set_parser = subparsers.add_parser("set", help="Interactively set credentials for one exchange.")
    set_parser.add_argument("exchange", choices=list(EXCHANGE_FIELDS.keys()))
    set_parser.add_argument(
        "--local", action="store_true",
        help=f"Write to the local fallback file ({LOCAL_KEY_FILE}) instead of AWS Secrets Manager.",
    )
    set_parser.add_argument(
        "--restart", action="store_true",
        help="Restart adlcontrol_container/assetcontrol_container after updating the secret.",
    )

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "set":
        cmd_set(args)


if __name__ == "__main__":
    main()
