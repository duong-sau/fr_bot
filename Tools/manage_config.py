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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manage_keys  # dung lai list/set exchange_key.json (co mask + getpass) thay vi viet lai

import requests
from rich import box
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from cli_style import console, print_error, print_header, print_info, print_section, print_success, print_warning
# Notification.Discord duoc import cuc bo (trong edit_discord_json), khong o dau file:
# no import Define, ma Define doc config.txt ngay luc import -> se crash truoc khi
# menu kip tao config.txt lan dau (muc 1 cua menu nay).

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
    entered = Prompt.ask(f"  [white]{label}[/]", default=current, console=console, show_default=True)
    return entered.strip() if entered else current


def prompt_exchange(label, current):
    return Prompt.ask(f"  [white]{label}[/]", choices=VALID_EXCHANGES, default=current, console=console)


def init_templates(interactive=True):
    """Tao cac file config mau con thieu. Khong bao gio ghi de file da co san."""
    print_section("Khởi tạo / tái tạo file config mẫu")
    created = []
    skipped = []

    cfg = read_config_txt()
    if cfg is None:
        if interactive:
            print_info("Chưa có config.txt -> nhập thông tin để tạo mới:")
            exchange1 = prompt_exchange("exchange1", "bitget")
            exchange2 = prompt_exchange("exchange2", "gate")
            ini_folder = prompt("Tên thư mục ini (vd 1_bitget_gate_ini)", DEFAULT_INI_FOLDER)
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

    console.print()
    if created:
        print_success("Đã tạo:")
        for p in created:
            console.print(f"    [success]+[/] {p}")
    else:
        print_info("(Không tạo file nào mới)")
    if skipped:
        print_info("Đã có sẵn, giữ nguyên:")
        for p in skipped:
            console.print(f"    [muted]=[/] {p}")
    console.print()
    print_warning(
        "exchange_key.json chỉ là khung rỗng (api_key/api_secret trống) - "
        "dùng `python Tools/manage_keys.py set <exchange> --local` để nhập key thật."
    )


def view_all():
    print_section("Tổng quan config hiện tại")
    console.print(f"[muted]_settings dir:[/] {SETTINGS_DIR}")
    cfg = read_config_txt()
    if cfg is None:
        print_error("config.txt: (chưa có)")
        return
    console.print(
        f"[accent]config.txt[/]: exchange1=[bold]{cfg['exchange1']}[/] "
        f"exchange2=[bold]{cfg['exchange2']}[/] ini_folder=[bold]{cfg['ini_folder']}[/]"
    )
    target_dir = ini_dir(cfg["ini_folder"])

    for label, path in [
        ("server.json", SERVER_JSON),
        ("balance.json", os.path.join(target_dir, "balance.json")),
        ("transfer.json", os.path.join(target_dir, "transfer.json")),
        ("config.json (discord)", os.path.join(target_dir, "config.json")),
    ]:
        console.print()
        console.print(f"[primary]{label}[/] [muted]{path}[/]")
        data = read_json(path)
        if data is None:
            print_error("  (chưa có)")
        else:
            console.print(Syntax(
                json.dumps(data, indent=2, ensure_ascii=False), "json",
                theme="material", background_color="default", word_wrap=True,
            ))

    console.print()
    console.print(f"[primary]exchange_key.json[/] [muted]{EXCHANGE_KEY_JSON}[/]")
    data = read_json(EXCHANGE_KEY_JSON)
    if data is None:
        print_error("  (chưa có)")
    else:
        table = Table(box=box.ROUNDED, border_style="primary")
        table.add_column("Exchange", style="bold #03DAC6")
        table.add_column("Field")
        table.add_column("Value", style="#9E9E9E")
        for exchange, fields in manage_keys.EXCHANGE_FIELDS.items():
            block = data.get(exchange, {})
            for i, field in enumerate(fields):
                table.add_row(exchange if i == 0 else "", field, manage_keys.mask(block.get(field, "")))
        console.print(table)


def edit_config_txt():
    print_section("Sửa config.txt")
    cfg = read_config_txt() or {"exchange1": "bitget", "exchange2": "gate", "ini_folder": DEFAULT_INI_FOLDER}
    exchange1 = prompt_exchange("exchange1", cfg["exchange1"])
    exchange2 = prompt_exchange("exchange2", cfg["exchange2"])
    ini_folder = prompt("Tên thư mục ini", cfg["ini_folder"])
    write_config_txt(exchange1, exchange2, ini_folder)
    print_success(f"Đã lưu {CONFIG_TXT}")


def edit_balance_json():
    print_section("Sửa balance.json")
    cfg = read_config_txt()
    if cfg is None:
        print_error("Chưa có config.txt, tạo trước đã (mục 1).")
        return
    path = os.path.join(ini_dir(cfg["ini_folder"]), "balance.json")
    data = read_json(path, dict(DEFAULT_BALANCE_JSON))
    current = data.get("max_diff_rate", 5)
    while True:
        raw = prompt("max_diff_rate (% lệch balance để kích hoạt transfer, 0-100)", str(current))
        try:
            value = float(raw)
        except ValueError:
            print_error("  Phải là số.")
            continue
        if not (0 < value < 100):
            print_error("  Phải trong khoảng (0, 100).")
            continue
        break
    data["max_diff_rate"] = value
    write_json(path, data)
    print_success(f"Đã lưu {path}")


def edit_transfer_json():
    print_section("Sửa transfer.json")
    cfg = read_config_txt()
    if cfg is None:
        print_error("Chưa có config.txt, tạo trước đã (mục 1).")
        return
    path = os.path.join(ini_dir(cfg["ini_folder"]), "transfer.json")
    data = read_json(path, {})
    for exchange in [cfg["exchange1"], cfg["exchange2"]]:
        block = data.get(exchange, {"address": "", "chain": "", "network": ""})
        console.print(f"\n[accent]\\[{exchange}][/]")
        block["address"] = prompt("address", block.get("address", ""))
        block["chain"] = prompt("chain", block.get("chain", ""))
        block["network"] = prompt("network", block.get("network", ""))
        data[exchange] = block
    write_json(path, data)
    print_success(f"Đã lưu {path}")


def edit_discord_json():
    print_section("Sửa config.json (Discord webhook)")
    cfg = read_config_txt()
    if cfg is None:
        print_error("Chưa có config.txt, tạo trước đã (mục 1).")
        return
    path = os.path.join(ini_dir(cfg["ini_folder"]), "config.json")
    data = read_json(path, dict(DEFAULT_DISCORD_JSON))
    current = data.get("discord", {}).get("webhook", "")
    webhook = prompt("Discord webhook URL", current)
    data["discord"] = {"webhook": webhook}
    write_json(path, data)
    print_success(f"Đã lưu {path}")

    if webhook:
        from Notification.Discord import send_to_discord
        console.print()
        print_info("Đang gửi tin nhắn test tới Discord webhook...")
        sent = send_to_discord(requests.Session(), webhook, "[config_menu] fr_bot: webhook hoạt động bình thường.")
        (print_success if sent else print_error)("Gửi thành công." if sent else "Gửi thất bại - kiểm tra lại webhook URL.")


def edit_server_json():
    print_section("Sửa server.json")
    data = read_json(SERVER_JSON, dict(DEFAULT_SERVER_JSON))
    services = data.get("microservices", [])
    for ms in services:
        console.print(f"\n[accent]\\[{ms.get('name')}][/]")
        ms["host"] = prompt("host", ms.get("host", ""))
    data["microservices"] = services
    write_json(SERVER_JSON, data)
    print_success(f"Đã lưu {SERVER_JSON}")


def edit_exchange_key():
    print_section("Sửa exchange_key.json")
    print_info(f"Sẽ sửa {EXCHANGE_KEY_JSON} (local fallback, không dùng AWS).")
    exchange = prompt_exchange("Exchange cần sửa", "bitget")
    manage_keys.cmd_set(argparse.Namespace(exchange=exchange, local=True, restart=False, skip_verify=False))


MENU_ITEMS = [
    ("1", "🧩", "Khởi tạo / tái tạo file config mẫu còn thiếu"),
    ("2", "👁", "Xem toàn bộ config hiện tại"),
    ("3", "🔀", "Sửa config.txt (exchange1 / exchange2 / ini folder)"),
    ("4", "⚖️", "Sửa balance.json (max_diff_rate)"),
    ("5", "💸", "Sửa transfer.json (địa chỉ nạp/rút mỗi sàn)"),
    ("6", "💬", "Sửa config.json (Discord webhook)"),
    ("7", "🖥️", "Sửa server.json (danh sách microservices)"),
    ("8", "🔑", "Sửa exchange_key.json (API key, local fallback)"),
    ("0", "🚪", "Thoát"),
]


def print_menu():
    table = Table(box=box.SIMPLE, show_header=False, expand=True, pad_edge=False)
    table.add_column(justify="center", style="bold #03DAC6", width=3)
    table.add_column(width=3)
    table.add_column(style="white")
    for key, icon, label in MENU_ITEMS:
        table.add_row(key, icon, label)
    console.print(Panel(table, title="[bold #BB86FC]MENU[/]", title_align="left", border_style="primary", box=box.ROUNDED))


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
        print_header("fr_bot CONFIG MANAGER", subtitle=SETTINGS_DIR)
        print_menu()
        choice = Prompt.ask("[accent]Chọn[/]", console=console).strip()
        if choice == "0":
            print_info("Tạm biệt!")
            break
        action = actions.get(choice)
        if action is None:
            print_error("Lựa chọn không hợp lệ.")
            continue
        try:
            action()
        except Exception as e:
            print_error(f"Lỗi: {e}")


if __name__ == "__main__":
    main()
