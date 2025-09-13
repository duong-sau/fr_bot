# Load config
import json
import os
import threading
import time

from Core.Tool import push_notification


class LogController:
    def __init__(self, log_file):
        self.log_file = log_file
        self.last_size = os.path.getsize(log_file) if os.path.exists(log_file) else 0

    def check_new_logs(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                f.seek(self.last_size)
                new_lines = f.readlines()
                self.last_size = f.tell()
                for line in new_lines:
                    if line.strip():
                        push_notification(line.strip())


class StatusController:
    def __init__(self, status_file):
        self.status_file = status_file
        self.status_json = {}

    def reload_status_file(self):
        with open(self.status_file, 'r', encoding='utf-8') as f:
            self.status_json = json.load(f)
        return self.status_json

    def get_status(self):
        return self.status_json

class MainController:
    def __init__(self):
        self.start_command = "~/fr_bot/code/start.sh"
        self.stop_command = "~/fr_bot/code/stop.sh"
        pass

    def start_bot(self):
        print(">>> Bot started")
        os.system(self.start_command)

    def stop_bot(self):
        print(">>> Bot stopped")
        os.system(self.stop_command)


class BotController:
    def __init__(self, log_file, status_file):
        push_notification('Start Controller bot')
        self.main_controller = MainController()
        self.status_controller = StatusController(status_file)
        self.log_controller = LogController(log_file)

        self.main_thread = threading.Thread(target=self.run)
        self.main_thread.daemon = True
        self.main_thread.start()

    def run(self):
        while True:
            self.log_controller.check_new_logs()
            time.sleep(5)

    def start_bot(self):
        self.main_controller.start_bot()

    def stop_bot(self):
        self.main_controller.stop_bot()

    def get_status(self):
        return self.status_controller.get_status()
