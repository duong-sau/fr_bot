import os
import sys
from enum import Enum
from Core.Define import convert_exchange_name_to_exchange

class SERVICE_NAME(Enum):
    """
    Enum for service names.
    """
    ASSET_CONTROL = "asset_control"

NULL = None
exchange1 = NULL
exchange2 = NULL

print(f"argv: {sys.argv}")
if len(sys.argv) < 4:
    print("Usage: python3 Asset.py <settings>")
    sys.exit(1)

setting_file = sys.argv[3]
if not os.path.exists(setting_file):
    raise FileNotFoundError(f"Setting file {setting_file} does not exist.")

with open(setting_file, 'r', encoding='utf-8') as f:
    settings = f.read().strip().splitlines()
    exchange1 = settings[0]
    exchange2 = settings[1]
    if exchange1 not in ['binance', 'bitget', 'bitget_sub', 'gate']:
        raise ValueError(f"Invalid exchange1: {exchange1}. Must be one of ['binance', 'bitget', 'bitget_sub', 'gate']")
    if exchange2 not in ['binance', 'bitget', 'bitget_sub', 'gate']:
        raise ValueError(f"Invalid exchange2: {exchange2}. Must be one of ['binance', 'bitget', 'bitget_sub', 'gate']")

    exchange1 = convert_exchange_name_to_exchange(exchange1)
    exchange2 = convert_exchange_name_to_exchange(exchange2)

    ini_path = settings[2]

if os.name == "nt":
    root_path = "C:\\"
else:
    root_path = "/home/ubuntu/fr_bot"

log_path = os.path.join(root_path, "logs")
tunel_log_path = os.path.join(log_path, "tunel")
asset_log_path = os.path.join(log_path, "asset")

transfer_done_file = os.path.join(log_path, "transfer_done.txt")

exchange_file_path = os.path.join(root_path, "code/settings", ini_path, "exchange.json")
transfer_info_path = os.path.join(root_path, "code/settings", ini_path, "transfer.json")
balance_info_path = os.path.join(root_path, "code/settings", ini_path,  "balance.json")