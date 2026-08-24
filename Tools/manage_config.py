"""
Man hinh CLI (menu) de tao lai file config mau va sua config trong _settings/
(nam ngoai repo, tai root_path co dinh - xem CLAUDE.md muc "Configuration").

root_path duoc tinh giong het Define.py:
    Windows -> C:\\job\\dim\\fr_bot\\
    Khac    -> /home/ubuntu/fr_bot

Usage:
    python Tools/manage_config.py            # mo menu tuong tac
    python Tools/manage_config.py init        # chi tao file mau con thieu, khong hoi gi, roi thoat
"""
import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import manage_keys  # dung lai list/set exchange_key.json (co mask + getpass) thay vi viet lai

if os.name == "nt":
    ROOT_PATH = "C:\\job\\dim\\fr_bot\\"
else:
    ROOT_PATH = "/home/ubuntu/fr_bot"

SETTINGS_DIR = os.path.join(ROOT_PATH, "code", "_settings")
CONFIG_TXT = os.path.join(SETTINGS_DIR, "config.txt")
SERVER_JSON = os.path.join(SETTINGS_DIR, "server.json")
EXCHANGE_KEY_JSON = manage_keys.LOCAL_KEY_FILE

VALID_EXCHANGES = ["binance", "bitget", "gate"]
DEFAULT_INI_FOLDER = "1_bitget_gate_ini"

DEFAULT_SERVER_JSON = {
    "microservices": [
        {"name": "adlcontrol", "host": "adlcontrol_container"},
        {"name": "assetcontrol", "host": "assetcontrol_container"},
        {"name": "discord", "host": "discord_shared_container"},
    ]
}

DEFAULT_BALANCE_JSON = {"max_diff_rate": 5}

DEFAULT_TRANSFER_JSON = {
    "binance": {"address": "", "chain": "", "network": ""},
    "bitget": {"address": "", "chain": "", "network": ""},
    "gate": {"address": "", "chain": "", "network": ""},
}

DEFAULT_DISCORD_JSON = {"discord": {"webhook": ""}}

# Khong co code nao doc file nay hien tai (legacy), chi tao cho du bo path Define.py tham chieu.
DEFAULT_TP_SL_JSON = {}


def ini_dir(ini_folder):
    return os.path.join(SETTINGS_DIR, ini_folder)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_config_txt():
    if not os.path.exists(CONFIG_TXT):
        return None
    with open(CONFIG_TXT, "r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    if len(lines) < 3:
        return None
    return {"exchange1": lines[0].strip(), "exchange2": lines[1].strip(), "ini_folder": lines[2].strip()}


def write_config_txt(exchange1, exchange2, ini_folder):
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    with open(CONFIG_TXT, "w", encoding="utf-8") as f:
        f.write(f"{exchange1}\n{exchange2}\n{ini_folder}\n")


def prompt(label, current=""):
    entered = input(f"{label} [{current}]: ").strip()
    return entered if entered else current


def prompt_exchange(label, current):
    while True:
        value = prompt(f"{label} ({'/'.join(VALID_EXCHANGES)})", current)
        if value in VALID_EXCHANGES:
            return value
        print(f"  Khong hop le, phai la mot trong: {', '.join(VALID_EXCHANGES)}")


def init_templates(interactive=True):
    """Tao cac file config mau con thieu. Khong bao gio ghi de file da co san."""
    created = []
    skipped = []

    cfg = read_config_txt()
    if cfg is None:
        if interactive:
            print("Chua co config.txt -> nhap thong tin de tao moi:")
            exchange1 = prompt_exchange("exchange1", "bitget")
            exchange2 = prompt_exchange("exchange2", "gate")
            ini_folder = prompt("Ten thu muc ini (vd 1_bitget_gate_ini)", DEFAULT_INI_FOLDER)
        else:
            exchange1, exchange2, ini_folder = "bitget", "gate", DEFAULT_INI_FOLDER
        write_config_txt(exchange1, exchange2, ini_folder)
        created.append(CONFIG_TXT)
        cfg = {"exchange1": exchange1, "exchange2": exchange2, "ini_folder": ini_folder}
    else:
        skipped.append(CONFIG_TXT)

    target_dir = ini_dir(cfg["ini_folder"])

    for path, default in [
        (SERVER_JSON, DEFAULT_SERVER_JSON),
        (os.path.join(target_dir, "balance.json"), DEFAULT_BALANCE_JSON),
        (os.path.join(target_dir, "transfer.json"), DEFAULT_TRANSFER_JSON),
        (os.path.join(target_dir, "config.json"), DEFAULT_DISCORD_JSON),
        (os.path.join(target_dir, "tp_sl.json"), DEFAULT_TP_SL_JSON),
    ]:
        if os.path.exists(path):
            skipped.append(path)
            continue
        write_json(path, default)
        created.append(path)

    if os.path.exists(EXCHANGE_KEY_JSON):
        skipped.append(EXCHANGE_KEY_JSON)
    else:
        write_json(EXCHANGE_KEY_JSON, {
            "binance": {"api_key": "", "api_secret": ""},
            "bitget": {"api_key": "", "api_secret": "", "password": ""},
            "gate": {"api_key": "", "api_secret": ""},
        })
        created.append(EXCHANGE_KEY_JSON)

    print("\nDa tao:" if created else "\n(Khong tao file nao moi)")
    for p in created:
        print(f"  + {p}")
    print("Da co san, giu nguyen:" if skipped else "")
    for p in skipped:
        print(f"  = {p}")
    print(
        "\nLuu y: exchange_key.json chi la khung rong (api_key/api_secret trong) - "
        "dung `python Tools/manage_keys.py set <exchange> --local` de nhap key that."
    )


def view_all():
    cfg = read_config_txt()
    print(f"\n_settings dir: {SETTINGS_DIR}")
    if cfg is None:
        print("config.txt: (chua co)")
        return
    print(f"config.txt: exchange1={cfg['exchange1']}, exchange2={cfg['exchange2']}, ini_folder={cfg['ini_folder']}")
    target_dir = ini_dir(cfg["ini_folder"])

    for label, path in [
        ("server.json", SERVER_JSON),
        ("balance.json", os.path.join(target_dir, "balance.json")),
        ("transfer.json", os.path.join(target_dir, "transfer.json")),
        ("config.json (discord)", os.path.join(target_dir, "config.json")),
    ]:
        print(f"\n{label} ({path}):")
        data = read_json(path)
        if data is None:
            print("  (chua co)")
        else:
            print("  " + json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\n  "))

    print(f"\nexchange_key.json ({EXCHANGE_KEY_JSON}):")
    data = read_json(EXCHANGE_KEY_JSON)
    if data is None:
        print("  (chua co)")
    else:
        for exchange, fields in manage_keys.EXCHANGE_FIELDS.items():
            block = data.get(exchange, {})
            print(f"  [{exchange}]")
            for field in fields:
                print(f"    {field}: {manage_keys.mask(block.get(field, ''))}")


def edit_config_txt():
    cfg = read_config_txt() or {"exchange1": "bitget", "exchange2": "gate", "ini_folder": DEFAULT_INI_FOLDER}
    exchange1 = prompt_exchange("exchange1", cfg["exchange1"])
    exchange2 = prompt_exchange("exchange2", cfg["exchange2"])
    ini_folder = prompt("Ten thu muc ini", cfg["ini_folder"])
    write_config_txt(exchange1, exchange2, ini_folder)
    print(f"Da luu {CONFIG_TXT}")


def edit_balance_json():
    cfg = read_config_txt()
    if cfg is None:
        print("Chua co config.txt, tao truoc da (muc 1).")
        return
    path = os.path.join(ini_dir(cfg["ini_folder"]), "balance.json")
    data = read_json(path, dict(DEFAULT_BALANCE_JSON))
    current = data.get("max_diff_rate", 5)
    while True:
        raw = prompt("max_diff_rate (% lech balance de kich hoat transfer, 0-100)", str(current))
        try:
            value = float(raw)
        except ValueError:
            print("  Phai la so.")
            continue
        if not (0 < value < 100):
            print("  Phai trong khoang (0, 100).")
            continue
        break
    data["max_diff_rate"] = value
    write_json(path, data)
    print(f"Da luu {path}")


def edit_transfer_json():
    cfg = read_config_txt()
    if cfg is None:
        print("Chua co config.txt, tao truoc da (muc 1).")
        return
    path = os.path.join(ini_dir(cfg["ini_folder"]), "transfer.json")
    data = read_json(path, {})
    for exchange in [cfg["exchange1"], cfg["exchange2"]]:
        block = data.get(exchange, {"address": "", "chain": "", "network": ""})
        print(f"\n[{exchange}]")
        block["address"] = prompt("  address", block.get("address", ""))
        block["chain"] = prompt("  chain", block.get("chain", ""))
        block["network"] = prompt("  network", block.get("network", ""))
        data[exchange] = block
    write_json(path, data)
    print(f"Da luu {path}")


def edit_discord_json():
    cfg = read_config_txt()
    if cfg is None:
        print("Chua co config.txt, tao truoc da (muc 1).")
        return
    path = os.path.join(ini_dir(cfg["ini_folder"]), "config.json")
    data = read_json(path, dict(DEFAULT_DISCORD_JSON))
    current = data.get("discord", {}).get("webhook", "")
    webhook = prompt("Discord webhook URL", current)
    data["discord"] = {"webhook": webhook}
    write_json(path, data)
    print(f"Da luu {path}")


def edit_server_json():
    data = read_json(SERVER_JSON, dict(DEFAULT_SERVER_JSON))
    services = data.get("microservices", [])
    for ms in services:
        print(f"\n[{ms.get('name')}]")
        ms["host"] = prompt("  host", ms.get("host", ""))
    data["microservices"] = services
    write_json(SERVER_JSON, data)
    print(f"Da luu {SERVER_JSON}")


def edit_exchange_key():
    print(f"Se sua {EXCHANGE_KEY_JSON} (local fallback, khong dung AWS).")
    exchange = prompt_exchange("Exchange can sua", "bitget")
    manage_keys.cmd_set(argparse.Namespace(exchange=exchange, local=True, restart=False))


MENU = """
=== fr_bot Config Manager ===
_settings dir: {settings_dir}

1. Khoi tao / tai tao file config mau con thieu
2. Xem toan bo config hien tai
3. Sua config.txt (exchange1 / exchange2 / ini folder)
4. Sua balance.json (max_diff_rate)
5. Sua transfer.json (dia chi nap/rut moi san)
6. Sua config.json (Discord webhook)
7. Sua server.json (danh sach microservices)
8. Sua exchange_key.json (API key, local fallback)
0. Thoat
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_templates(interactive=False)
        return

    actions = {
        "1": init_templates,
        "2": view_all,
        "3": edit_config_txt,
        "4": edit_balance_json,
        "5": edit_transfer_json,
        "6": edit_discord_json,
        "7": edit_server_json,
        "8": edit_exchange_key,
    }

    while True:
        print(MENU.format(settings_dir=SETTINGS_DIR))
        choice = input("Chon: ").strip()
        if choice == "0":
            break
        action = actions.get(choice)
        if action is None:
            print("Lua chon khong hop le.")
            continue
        try:
            action()
        except Exception as e:
            print(f"Loi: {e}")


if __name__ == "__main__":
    main()
