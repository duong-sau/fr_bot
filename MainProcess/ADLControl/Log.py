from Core.Logger import log_info, LogService


def adl_log(message):
    log_info(LogService.ADL, str(message))
