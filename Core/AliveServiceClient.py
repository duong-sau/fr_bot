import requests

from Core.StopTimer import StopTimer

import json
import os

config_path = os.path.join(os.path.dirname(__file__), '..', 'ini', 'Config.json')
with open(config_path, 'r') as f:
    config = json.load(f)
server_url = config['alive_server']['url']

class AliveServiceClient:
    def __init__(self, service_name):
        self.service_name = service_name
        self.ping_interval = 5  # seconds
        self.ping_timer = StopTimer()
        self.ping_timer.start()

    def ping(self):
        """
        Simulate a ping to the service.
        """
        # print(f"Pinging {self.service_name} service...")
        try:
            requests.get(f"{server_url}", params={"name": self.service_name})
        except Exception as e:
            print(f"Failed to ping {self.service_name} service: {e}")
        #
        # if response.status_code == 200:
        #     # print(f"{self.service_name} service is alive.")
        # else:
        #     # print(f"Failed to ping {self.service_name} service. Status code: {response.status_code}")

    def tick(self):
        """
        Periodically ping the service to check if it's alive.
        """
        if self.ping_timer.check_elapsed_time(self.ping_interval):
            self.ping()
