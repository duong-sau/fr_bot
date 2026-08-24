"""
Style dùng chung cho các CLI tương tác trong Tools/ (manage_config.py, manage_keys.py)
— bảng màu lấy theo Material Design Dark theme: tím #BB86FC làm primary, teal #03DAC6
làm accent, cùng success/error/warning chuẩn Material (#4CAF50/#CF6679/#FFC107).

Import module này sẽ tự bật UTF-8 cho stdout/stderr trước khi tạo Console — nếu không,
icon/emoji và text tiếng Việt sẽ crash trên console Windows mặc định (cp1252).
"""
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.theme import Theme

from Core.Tool import ensure_utf8_stdout

ensure_utf8_stdout()

MATERIAL_THEME = Theme({
    "primary": "bold #BB86FC",
    "accent": "#03DAC6",
    "success": "bold #4CAF50",
    "error": "bold #CF6679",
    "warning": "bold #FFC107",
    "muted": "#9E9E9E",
})

console = Console(theme=MATERIAL_THEME)


def print_header(title: str, subtitle: str = ""):
    console.print()
    console.print(Panel(
        f"[bold white]{title}[/]",
        style="on #6200EE",
        border_style="primary",
        box=box.ROUNDED,
        expand=True,
        padding=(0, 2),
    ))
    if subtitle:
        console.print(f"  [muted]{subtitle}[/]")


def print_section(title: str):
    console.print(Rule(f"[primary]{title}[/]", style="primary"))


def print_success(message: str):
    console.print(f"[success]✓[/] {message}")


def print_error(message: str):
    console.print(f"[error]✗[/] {message}")


def print_warning(message: str):
    console.print(f"[warning]![/] {message}")


def print_info(message: str):
    console.print(f"[accent]›[/] {message}")
