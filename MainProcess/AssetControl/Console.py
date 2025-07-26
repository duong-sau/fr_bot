import curses
window_height = 16
window_width = 80

def draw_positions_table(stdscr, asset_info, status):

    stdscr.addstr(0, 0, "Binance-Bitget Asset Balance Process", curses.A_BOLD)
    stdscr.hline(1, 0, curses.ACS_HLINE, window_width)
    # Draw balance bar between total assets on Binance and Bitget
    binance_total = float(asset_info['binance'].total_margin_balance)
    bitget_total = float(asset_info['bitget'].total_margin_balance)
    max_total = max(binance_total + bitget_total, 1)
    bar_width = int( window_width)
    binance_bar = int(bar_width * binance_total / max_total)
    bitget_bar = int(bar_width * bitget_total / max_total)

    stdscr.addstr(3, 0, f"Binance: {binance_total:.4f} USDT", curses.A_BOLD)
    stdscr.addstr(4, 0, f"Bitget : {bitget_total:.4f} USDT", curses.A_BOLD)
    stdscr.addstr(5, 0, f"SUM    : {(binance_total + bitget_total):.4f} USDT", curses.A_BOLD)

    stdscr.addstr(6, 0, f"BINANCE", curses.A_BOLD| curses.color_pair(1))
    stdscr.addstr(6, window_width - 6, f"BITGET", curses.A_BOLD | curses.color_pair(2))
    stdscr.addstr(7, 0, "[" + "#" * binance_bar, curses.color_pair(1))
    stdscr.addstr(7, 0 + binance_bar, "#" * bitget_bar + "]", curses.color_pair(2))
    min_balance = float(asset_info['estimated_min_balance'])
    min_balance_bar = int(bar_width * 10 * min_balance / max_total / 10)
    stdscr.addstr(8, 0, f"Estimated Min Balance: {min_balance}", curses.A_BOLD)

    stdscr.addstr(9, 0, "[" + "|" * min_balance_bar, curses.color_pair(1))
    stdscr.addstr(9, bar_width - min_balance_bar, "|" * min_balance_bar + "]", curses.color_pair(2))


    if status:
        stdscr.addstr(10, 0, "Transfer in progress...", curses.A_BOLD | curses.color_pair(3))
    else:
        stdscr.addstr(10, 0, "                       ", curses.A_BOLD | curses.color_pair(4))


    stdscr.refresh()
