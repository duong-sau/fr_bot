import os
import logging
from logging.handlers import RotatingFileHandler
from enum import Enum

from Define import log_path, shared_log_path, discord_simple_log_path

class LogService(Enum):
    SERVER = "server"
    ADL = "adl"
    ASSET = "asset"
    TUNEL = "tunel"
    TP_SL = "tp_sl"

_initialized = {}

DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5MB
DEFAULT_BACKUP_COUNT = 3


def _ensure_parent(file_path: str):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _ensure_dir(dir_path: str):
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def _level_from_env() -> int:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def _discord_level_from_env() -> int:
    level = os.getenv("DISCORD_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def get_logger(service: LogService) -> logging.Logger:
    """
    Trả về logger cho service. Logger này sẽ ghi:
    - shared_log_path (đầy đủ level theo LOG_LEVEL)
    - discord_simple_log_path (đơn giản, chỉ INFO+ mặc định, có thể chỉnh DISCORD_LOG_LEVEL)
    - file log riêng của service (syslog.log)
    Định dạng chung: YYYY-mm-dd HH:MM:SS | LEVEL | NAME | message
    """
    name = f"frbot.{service.value}"
    if name in _initialized:
        return logging.getLogger(name)

    logger = logging.getLogger(name)
    logger.setLevel(_level_from_env())
    logger.propagate = False  # tránh ghi trùng lên root

    # Formatter chi tiết (cho shared và service)
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Formatter đơn giản (cho Discord)
    simple_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler shared log (ghi mọi service, theo LOG_LEVEL)
    _ensure_parent(shared_log_path)
    shared_handler = RotatingFileHandler(shared_log_path, maxBytes=DEFAULT_MAX_BYTES, backupCount=DEFAULT_BACKUP_COUNT, encoding='utf-8')
    shared_handler.setFormatter(detailed_formatter)
    shared_handler.setLevel(_level_from_env())
    logger.addHandler(shared_handler)

    # Handler simple dành cho Discord (mặc định INFO+, có thể chỉnh bằng DISCORD_LOG_LEVEL)
    _ensure_parent(discord_simple_log_path)
    discord_handler = RotatingFileHandler(discord_simple_log_path, maxBytes=DEFAULT_MAX_BYTES, backupCount=DEFAULT_BACKUP_COUNT, encoding='utf-8')
    discord_handler.setFormatter(simple_formatter)
    discord_handler.setLevel(_discord_level_from_env())
    logger.addHandler(discord_handler)

    # Handler theo service -> logs/{service}/syslog.log
    service_dir = os.path.join(log_path, service.value)
    _ensure_dir(service_dir)
    service_file = os.path.join(service_dir, 'syslog.log')
    _ensure_parent(service_file)
    service_handler = RotatingFileHandler(service_file, maxBytes=DEFAULT_MAX_BYTES, backupCount=DEFAULT_BACKUP_COUNT, encoding='utf-8')
    service_handler.setFormatter(detailed_formatter)
    service_handler.setLevel(_level_from_env())
    logger.addHandler(service_handler)

    _initialized[name] = True
    return logger


def log_info(service: LogService, message: str):
    get_logger(service).info(message)


def log_warning(service: LogService, message: str):
    get_logger(service).warning(message)


def log_error(service: LogService, message: str):
    get_logger(service).error(message)


def log_debug(service: LogService, message: str):
    get_logger(service).debug(message)
