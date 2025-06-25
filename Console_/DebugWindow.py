import io


class CursesStream(io.TextIOBase):
    def __init__(self, window):
        self.window = window

    def write(self, msg):
        if msg:  # Chỉ xử lý nếu có nội dung
            self.window.addstr(msg)
            self.window.refresh()