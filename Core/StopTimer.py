from time import time
class StopTimer:
    """
    A simple timer class to measure elapsed time.
    """

    def __init__(self):
        self.start_time = None

    def start(self):
        """Start the timer."""
        self.start_time = time()

    def stop(self):
        """Stop the timer and return the elapsed time in seconds."""
        self.start_time = None

    def check_elapsed_time(self, interval):
        """Check the elapsed time without stopping the timer."""
        if self.start_time is None:
            raise ValueError("Timer has not been started.")
        if (time() - self.start_time) > interval :
            self.start_time = time()
            return True
        return False