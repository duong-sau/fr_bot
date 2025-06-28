import sys
import curses
import time
import ccxt
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Core")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Console_")))

from Core.Define import EXCHANGE
from FrAbitrageCore import FrAbitrageCore
from Tracker.BinanceTracker import BinanceTracker
from Tracker.BitgetTracker import BitgetTracker
from Tracker.GateIOTracker import GateIOTracker
from Tracker.OKXTracker import OKXTracker

def draw_positions_table(stdscr, abitrage_pairs, asset_info):
    stdscr.clear()
    stdscr.addstr(0, 0, "FrAbitrage Positions", curses.A_BOLD)

    # Headers
    headers = ["Symbol", "LongExchange", "ShortExchange", "amount", 'exchange1_pnl', 'exchange2_pnl',
               'long_funding', 'short_funding', 'funding_diff' 'paied_funding']
    for idx, header in enumerate(headers):
        stdscr.addstr(2, idx * 15, header, curses.A_BOLD)
    # Table data
    for i, pair in enumerate(abitrage_pairs):
        y = 3 + i  # Vị trí dòng hiện tại

        # Dữ liệu từng cột
        stdscr.addstr(y, 0, str(pair.long_position.symbol))
        stdscr.addstr(y, 15, str(pair.long_position.exchange.name))
        stdscr.addstr(y, 30, str(pair.short_position.exchange.name))
        stdscr.addstr(y, 45, str(pair.long_position.amount_))
        stdscr.addstr(y, 60, f"{pair.unreal_pnl:.2f} %")
        stdscr.addstr(y, 75, f"{-pair.unreal_pnl:.2f} %")
        stdscr.addstr(y, 90, str(getattr(pair, 'long_funding', '')))
        stdscr.addstr(y, 105, str(getattr(pair, 'short_funding', '')))
        stdscr.addstr(y, 120, str(getattr(pair, 'funding_diff', '')), curses.color_pair(1))


        stdscr.addstr(y, 130, str(pair.long_position.paid_funding + pair.short_position.paid_funding))

    # Draw balance bar between total assets on Binance and Bitget
    binance_total = float(asset_info['binance'].total_margin_balance)
    bitget_total = float(asset_info['bitget'].total_margin_balance)
    max_total = max(binance_total, bitget_total, 1)
    bar_width = 50
    binance_bar = int(bar_width * binance_total / max_total)
    bitget_bar = int(bar_width * bitget_total / max_total)

    stdscr.addstr(20, 0, f"Binance: {binance_total:.4f} USDT", curses.A_BOLD)
    stdscr.addstr(20, 30, "[" + "#" * binance_bar + " " * (bar_width - binance_bar), curses.color_pair(1))
    stdscr.addstr(20, 30 + binance_bar, "#" * bitget_bar + " " * (bar_width - bitget_bar) + "]", curses.color_pair(2))
    stdscr.addstr(20, 120, f"Bitget: {bitget_total:.4f} USDT", curses.A_BOLD)
    stdscr.addstr(22, 0, f"SUM : {(binance_total + bitget_total):.4f}", curses.A_BOLD)


    stdscr.refresh()

tracker = BinanceTracker()
binance_open_positions = tracker.get_open_positions()

bitget_tracker = BitgetTracker()
bitget_open_positions = bitget_tracker.get_open_positions()

fr_abitrage_core = FrAbitrageCore()
fr_abitrage_core.check_position(binance_open_positions + bitget_open_positions)

client = ccxt.binance({'options': {
    'defaultType': 'future',  # Đảm bảo đang làm việc với futures
}})

for pos in fr_abitrage_core.positions:
    symbol = pos.long_position.symbol
    mark_price_data = client.fetch_funding_rate(symbol=symbol)
    mark_price = float(mark_price_data['markPrice'])
    entry_price = float(pos.long_position.entry_price)
    amount = round(float(pos.long_position.amount * mark_price), 2)
    pos.long_position.amount_ = amount
    # Assuming long position; for short, reverse the calculation
    unreal_pnl = (mark_price - entry_price) / entry_price * 100 * pos.long_position.margin
    pos.unreal_pnl = round(unreal_pnl, 2)





def draw_main(stdscr):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Màu dương
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Màu âm

    while True:

        binance_asset_info = tracker.get_cross_margin_account_info()
        bitget_asset_info = bitget_tracker.get_cross_margin_account_info()
        import ast

        # with open('fundingrate.csv', 'r', encoding='utf-8') as f:
        #     funding_data = ast.literal_eval(f.read())
        # funding_diff = []
        # for symbol, rates in funding_data.items():
        #     if 'binance' in rates and 'bitget' in rates:
        #         diff = round(rates['binance'] - rates['bitget'], 2)
        #         funding_diff.append((symbol, rates['binance'], rates['bitget'], diff))
        #
        #     # Merge funding_diff into positions by symbol
        #     for pos in fr_abitrage_core.positions:
        #         for symbol, binance_rate, bitget_rate, diff in funding_diff:
        #             if pos.long_position.symbol == symbol:
        #                 if pos.long_position.exchange == EXCHANGE.BINANCE:
        #                     pos.long_funding = binance_rate
        #                     pos.short_funding = bitget_rate
        #                     pos.funding_diff = - diff
        #                 elif pos.long_position.exchange == EXCHANGE.BITGET:
        #                     pos.long_funding = bitget_rate
        #                     pos.short_funding = binance_rate
        #                     pos.funding_diff = diff
        #                 break

        asset = {
            'binance': binance_asset_info,
            'bitget': bitget_asset_info,
            # 'okx': okx_asset_info,
            # 'gate': gate_asset_info
        }


        draw_positions_table(stdscr, fr_abitrage_core.positions, asset)
        time.sleep(5)
if __name__ == '__main__':
    binance_asset_info = tracker.get_cross_margin_account_info()
    bitget_asset_info = bitget_tracker.get_cross_margin_account_info()
    # okx_tracker = OKXTracker()
    # okx_open_positions = okx_tracker.get_open_positions()

    # gate_tracker = GateIOTracker()
    # gate_open_positions = gate_tracker.get_open_positions()

    curses.wrapper(draw_main)

