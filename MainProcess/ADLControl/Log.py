from Core.Tool import write_log
from Define import adl_log_path


def adl_log(message):
    sys_log = adl_log_path
    write_log(message, sys_log)
