import os
import subprocess
import curses
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Core")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Console_")))

from Console_.DebugWindow import CursesStream
from Core.AliveServiceClient import AliveServiceClient
from Define import asset_log_path, transfer_done_file, SERVICE_NAME
from Tool import write_log
from Tracker.BinanceTracker import BinanceTracker
from Tracker.BitgetTracker import BitgetTracker
from AssetControl.Console import draw_positions_table

start_time = time.time()

def asset_control_log(message):
    log_file = os.path.join(asset_log_path, f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(start_time))}.log")
    write_log(message, log_file)

def start_cruses():
    stdscr = curses.initscr()  # Khởi tạo curses
    curses.noecho()            # Tắt chế độ hiển thị phím
    curses.cbreak()            # Bật chế độ xử lý ngay sau khi nhập
    stdscr.keypad(True)        # Bật chế độ bàn phím nâng cao
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

    std_out_height, std_out_width = 20, 80
    start_y, start_x = 30, 0
    output_win = curses.newwin(std_out_height, std_out_width, start_y, start_x)
    output_win.border()
    output_win.refresh()
    sys.stdout = CursesStream(output_win)
    sys.stderr = CursesStream(output_win)

    return stdscr

def end_cruses(stdscr):
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

class AssetProcess:
    def __init__(self, binance_tracker, bitget_tracker):
        self.binance_tracker = binance_tracker
        self.bitget_tracker = bitget_tracker
        self.in_transfer = False  # Biến để kiểm tra xem có đang trong quá trình chuyển tiền hay không
        self.asset = {}
        self.process = None  # Biến để lưu trữ tiến trình chuyển tiền
        self.tick()


    def transfer(self, from_exchange, to_exchange, amount):
        if self.in_transfer:
            raise Exception("Transfer is already in progress, please wait until it completes.")
        self.in_transfer = True  # Đánh dấu là đang trong quá trình chuyển tiền

        # Xoá file transfer_done_file nếu tồn tại và tạo lại file rỗng
        with open(transfer_done_file, 'w', encoding='utf-8') as f:
            f.write('WAIT\n')

        asset_control_log(f"Transfer {amount} USDT from {from_exchange} to {to_exchange}")
        # script_path = os.path.abspath("AssetControl/Transfer.py")
        script_path = "Transfer.py"
        # subprocess.Popen(
        #     ['python3', script_path, from_exchange, to_exchange, str(amount)],
        #     stdout=subprocess.DEVNULL,  # Không kế thừa stdout
        #     stderr=subprocess.DEVNULL,  # Không kế thừa stderr
        #     stdin=subprocess.DEVNULL,  # Không kế thừa stdin
        #     close_fds=True  # Đóng các file descriptor không cần thiết (Unix)
        # )
        venv_python = sys.executable
        self.process = subprocess.Popen(
            [venv_python, script_path, from_exchange, to_exchange, str(amount)],
            stdout=subprocess.PIPE,  # Không kế thừa stdout
            stderr=subprocess.PIPE,  # Không kế thừa stderr
        )

    def check_transfer_status(self):
        """
        Kiểm tra trạng thái chuyển tiền.
        Nếu quá trình chuyển tiền đã hoàn thành, trả về True, ngược lại trả về False.
        """
        with open(transfer_done_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line == 'OK':
                asset_control_log("Transfer completed successfully.")
                self.in_transfer = False
                return True
            elif first_line == 'ERROR':
                asset_control_log("Transfer failed, please check the logs for details.")
                self.in_transfer = False
                return True
            else:
                return False


    def tick(self):
        binance_asset_info = self.binance_tracker.get_cross_margin_account_info()
        bitget_asset_info = self.bitget_tracker.get_cross_margin_account_info()

        total = binance_asset_info.total_margin_balance + bitget_asset_info.total_margin_balance
        min_balance = total/2 - total* 0.05
        self.asset = {
            'binance': binance_asset_info,
            'bitget': bitget_asset_info,
            'estimated_min_balance': min_balance,
        }

        if not self.in_transfer:
            # Nếu chênh lệch giữa 2 sàn quá 20% tổng asset thì chuyển lượng chênh lệch (làm tròn đến 10 USDT) từ sàn ít hơn sang sàn nhiều hơn
            total_asset = binance_asset_info.total_margin_balance + bitget_asset_info.total_margin_balance
            diff = abs(binance_asset_info.total_margin_balance - bitget_asset_info.total_margin_balance)
            if total_asset > 0 and diff / total_asset > 0.05:
                move_amount = int(diff/2 // 10) * 10  # Làm tròn xuống đến 10 USDT
                if move_amount == 0:
                    raise ValueError("The difference is too small to transfer, please check your balances.")
                if binance_asset_info.total_margin_balance > bitget_asset_info.total_margin_balance:
                    self.transfer('binance', 'bitget', move_amount)
                else:
                    self.transfer('bitget', 'binance', move_amount)

        if self.in_transfer:
            self.check_transfer_status()

    def get_asset_info(self):
        return self.asset

    def get_status(self):
        return self.in_transfer


if __name__ == '__main__':
    stdscr = start_cruses()
    # stdscr = None
    venv_python = sys.executable
    # log_file = os.path.join(asset_log_path, f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(start_time))}.log")
    # subprocess.Popen(
    #     [venv_python, "Discord.py", log_file],
    #     stdout=subprocess.PIPE,  # Không kế thừa stdout
    #     stderr=subprocess.PIPE,  # Không kế thừa stderr
    # )
    asset_control_log("Starting asset balance process...")

    binance_tracker = BinanceTracker()
    bitget_tracker = BitgetTracker()
    asset_process = AssetProcess(binance_tracker, bitget_tracker)

    alive_service_client = AliveServiceClient(SERVICE_NAME.ASSET_CONTROL.value)

    try:

        while True:
            alive_service_client.tick()
            asset_process.tick()
            asset = asset_process.get_asset_info()
            status = asset_process.get_status()
            draw_positions_table(stdscr, asset, status)
            time.sleep(5)
    except KeyboardInterrupt:
        asset_control_log("Process interrupted by user (Ctrl+C). Exiting...")
    end_cruses(stdscr)
