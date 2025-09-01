import csv
import sys
import time
from datetime import datetime

import ccxt
import os
import pandas as pd
import schedule

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from MainProcess.PositionView.FrAbitrageCore import FrAbitrageCore
from Core.Exchange.Exchange import ExchangeManager
from Core.Tracker.BitgetTracker import BitgetTracker
from Core.Tracker.GateIOTracker import GateIOTracker
from Define import exchange1, exchange2




exchange_manager = ExchangeManager(exchange1, exchange2)

bitget_tracker = BitgetTracker(exchange_manager.bitget_exchange)
bitget_opening_position = bitget_tracker.get_open_positions()

gate_tracker = GateIOTracker(exchange_manager.gate_exchange)
gate_opening_position = gate_tracker.get_open_positions()

fr_abitrage_core = FrAbitrageCore()
fr_abitrage_core.check_position(bitget_opening_position + gate_opening_position)


def main_function():
    file_path = 'funding_profit.csv'
    today = time.strftime('%Y-%m-%d', time.localtime())

    col_bitget = f'{today}_bitget'
    col_gate   = f'{today}_gate'

    # 1) Gom lợi nhuận theo symbol
    agg = {}
    for pos in fr_abitrage_core.positions:
        symbol = pos.long_position.symbol

        bitget_paid = float(getattr(pos.long_position, 'paid_funding', 0) or 0)
        gate_paid   = float(getattr(pos.short_position, 'paid_funding', 0) or 0)

        if symbol not in agg:
            agg[symbol] = {'bitget': 0.0, 'gate': 0.0}
        agg[symbol]['bitget'] += bitget_paid
        agg[symbol]['gate']   += gate_paid

    # 2) DataFrame cho ngày hôm nay
    rows = []
    for symbol, v in sorted(agg.items()):
        rows.append({
            'symbol': symbol,
            col_bitget: v['bitget'],
            col_gate: v['gate'],
            'current_profit': v['bitget'] + v['gate']
        })

    # (tuỳ chọn) thêm dòng tổng
    rows.append({
        'symbol': '__TOTAL__',
        col_bitget: sum(v['bitget'] for v in agg.values()),
        col_gate:   sum(v['gate'] for v in agg.values()),
        'current_profit': sum(v['bitget'] + v['gate'] for v in agg.values())
    })

    df_today = pd.DataFrame(rows).set_index('symbol')

    # 3) Gộp với file cũ
    if os.path.isfile(file_path):
        df_old = pd.read_csv(file_path)
        if 'symbol' in df_old.columns:
            df_old = df_old.set_index('symbol')
        # Gộp dữ liệu
        if 'current_profit' in df_old.columns:
            df_old = df_old.drop(columns=['current_profit'])
        if col_bitget in df_old.columns:
            df_old = df_old.drop(columns=[col_bitget])
        if col_gate in df_old.columns:
            df_old = df_old.drop(columns=[col_gate])
        df_all = df_old.join(df_today[[col_bitget, col_gate, 'current_profit']], how='outer')

        # Update nếu cột hôm nay đã tồn tại
        for c in [col_bitget, col_gate, 'current_profit']:
            if c in df_all.columns:
                df_all[c].update(df_today[c])
    else:
        df_all = df_today

    # 4) Sắp xếp cột theo block ngày
    def sort_key(col: str):
        if col == 'current_profit':
            return (datetime.max, 'z')  # luôn ở cuối
        if col.endswith('_bitget'):
            # lấy ngày ở phần đầu "YYYY-MM-DD"
            day = datetime.strptime(col[:10], "%Y-%m-%d")
            return (day, 'a')  # bitget trước
        if col.endswith('_gate'):
            day = datetime.strptime(col[:10], "%Y-%m-%d")
            return (day, 'b')  # gate sau
        return (datetime.max, 'z')

    ordered_cols = sorted([c for c in df_all.columns if c != 'symbol'], key=sort_key)
    df_all = df_all[ordered_cols]

    # 5) Lưu file
    df_all.sort_index().to_csv(file_path, encoding='utf-8', float_format='%.10f')
    print(f"Report updated: {file_path} (added columns: {col_bitget}, {col_gate}, current_profit)")
if __name__ == '__main__':
    main_function()
    for hour in [9, 13, 17, 21, 1, 5]:
        schedule.every().day.at(f"{hour:02d}:05").do(main_function)

    while True:
        schedule.run_pending()
        time.sleep(1)