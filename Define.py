import os
from enum import Enum

if os.name == "nt":
    root_path = r"C:\Logs"
else:
    root_path = "/home/ubuntu/fr_bot"

log_path = os.path.join(root_path, "logs")
tunel_log_path = os.path.join(log_path, "tunel")
asset_log_path = os.path.join(log_path, "asset")

transfer_done_file = os.path.join(log_path, "transfer_done.txt")

exchange_file_path = os.path.join(root_path, "code", "ini", "exchange.json")

class SERVICE_NAME(Enum):
    """
    Enum for service names.
    """
    ASSET_CONTROL = "asset_control"