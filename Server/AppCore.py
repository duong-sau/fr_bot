import threading
import time

from Server.MicroserviceManager import MicroserviceManager


class AppCore:
    def __init__(self):
        self.microservice_manager = MicroserviceManager()
        self.run()

    def get_microservices(self):
        services =  self.microservice_manager.get_microservices()
        return [ms.get_model() for ms in services]

    def start_microservice(self, service_id):
        return self.microservice_manager.start_microservice(service_id)

    def stop_microservice(self, service_id):
        return self.microservice_manager.stop_microservice(service_id)

    def main_loop(self):
        while True:
            for microservice in self.microservice_manager.get_microservices():
                microservice.ping()
            time.sleep(5)

    def run(self):
        main_thread = threading.Thread(target=self.main_loop)
        main_thread.start()