from Core.StopTimer import StopTimer

class AliveServiceClient:
    def __init__(self, service_name):
        self.service_name = service_name
        self.ping_interval = 5  # seconds
        self.ping_timer = StopTimer()
        self.ping_timer.start()

    def ping(self, params=None):
        """
        Simulate a ping to the service.
        """
        return True

    def tick(self, params=None):
        """
        Periodically ping the service to check if it's alive.
        """
        if self.ping_timer.check_elapsed_time(self.ping_interval):
            self.ping(params)
