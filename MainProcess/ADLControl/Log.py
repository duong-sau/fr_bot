from Core.Tool import write_log
from Define import shared_log_path


def adl_log(message):
    write_log(message, shared_log_path)
