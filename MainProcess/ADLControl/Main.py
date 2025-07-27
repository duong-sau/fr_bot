import asyncio
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Core.Exchange.Exchange import ExchangeManager
from Core.Tool import try_this
from Define import exchange1, exchange2, root_path
from MainProcess.ADLControl.Log import adl_log
from MainProcess.ADLControl.Order import close_position_gate, close_position_bitget, fetch_position_bitget, \
    fetch_position_gate


class ADLController:
    def __init__(self, exchange_manager):

        self.exchangeManager = exchange_manager

        self.bitget_pro = exchange_manager.bitget_pro
        self.gate_pro = exchange_manager.gate_pro

        self.bitget_exchange = exchange_manager.bitget_exchange
        self.gate_exchange = exchange_manager.gate_exchange

        self.lock = asyncio.Lock()
        self.positions = {}
        self.error_count = 0


    def check_position_change(self, symbol):
        bitget_total, bitget_side, bitget_contract_size = fetch_position_bitget(self.bitget_exchange, symbol)
        gate_total, gate_side, gate_contract_size = fetch_position_gate(self.gate_exchange, symbol)

        if gate_total == 0 and bitget_total == 0:
            return

        adl_log(f"Gate total: {gate_total}, Bitget total: {bitget_total}, Symbol: {symbol}, Gate side: {gate_side}, Bitget side: {bitget_side}")

        if gate_total > bitget_total:
            diff = gate_total - bitget_total
            adl_log(f"Gate has more position: {diff} {symbol}")
            diff_contras = diff / bitget_contract_size
            close_position_gate(self.gate_exchange, symbol, gate_side, diff_contras)
        elif bitget_total > gate_total:
            diff = bitget_total - gate_total
            adl_log(f"Bitget has more position: {diff} {symbol}")
            diff_contras = diff / gate_contract_size
            close_position_bitget(self.bitget_exchange, symbol, bitget_side, diff_contras)

    async def sync_hedge(self, exchange, symbols):
        await exchange.load_markets()
        adl_log(f"Listening for position changes on {exchange.id}...")

        self.error_count = 0

        while True:
            try:
                pos = await exchange.watch_positions(symbols=symbols)
                print(pos)

                # Check for symbols not present in current positions
                current_symbols = {p['symbol'] for p in pos}
                for symbol in symbols:
                    if symbol not in current_symbols:
                        async with self.lock:
                            old_bitget_size = self.positions.get(symbol, {}).get('bitget_size', 0)
                            old_gate_size = self.positions.get(symbol, {}).get('gate_size', 0)
                        if exchange.id == 'bitget' and old_bitget_size != 0:
                            adl_log(f"Bitget position changed for {symbol}: {old_bitget_size} -> 0")    
                            try_this(self.check_position_change, params={'symbol': symbol}, log_func=adl_log, retries=5,
                                     delay=1)
                            async with self.lock:
                                self.positions.setdefault(symbol, {})['bitget_size'] = 0
                        elif exchange.id == 'gateio' and old_gate_size != 0:
                            adl_log(f"GateIO position changed for {symbol}: {old_gate_size} -> 0")
                            try_this(self.check_position_change, params={'symbol': symbol}, log_func=adl_log, retries=5,
                                     delay=1)
                            async with self.lock:
                                self.positions.setdefault(symbol, {})['gate_size'] = 0

                for p in pos:
                    p_symbol = p['symbol']
                    p_size = float(p['contracts']) * float(p['contractSize'])

                    async with self.lock:
                        if p_symbol not in self.positions:
                            self.positions[p_symbol] = {
                                'gate_size': p_size,
                                'bitget_size': p_size,
                            }
                    old_bitget_size = self.positions[p_symbol]['bitget_size']
                    old_gate_size = self.positions[p_symbol]['gate_size']

                    async with self.lock:
                        if exchange.id == 'bitget':
                            self.positions[p_symbol]['bitget_size'] = p_size
                        elif exchange.id == 'gateio':
                            self.positions[p_symbol]['gate_size'] = p_size
                        else:
                            adl_log(f"Unknown exchange id: {exchange.id}")
                            sys.exit(1)

                    if exchange.id == 'bitget':
                        if old_bitget_size != p_size:
                            adl_log(f"Bitget position changed for {p_symbol}: {old_bitget_size} -> {p_size}")
                            try_this(self.check_position_change, params={'symbol': p_symbol}, log_func=adl_log,
                                     retries=5, delay=1)
                        self.positions[p_symbol]['bitget_size'] = p_size
                    elif exchange.id == 'gateio':
                        if old_gate_size != p_size:
                            adl_log(f"GateIO position changed for {p_symbol}: {old_gate_size} -> {p_size}")
                            try_this(self.check_position_change, params={'symbol': p_symbol}, log_func=adl_log,
                                     retries=5, delay=1)
                    else:
                        adl_log(f"Unknown exchange id: {exchange.id}")
                        sys.exit(1)
                self.error_count = self.error_count - 1 if self.error_count > 1 else 0

                for p in pos:
                    p_symbol = p['symbol']
                    p_size = float(p['contracts']) * float(p['contractSize'])

                    async with self.lock:
                        if p_symbol not in self.positions:
                            self.positions[p_symbol] = {
                                'gate_size': p_size,
                                'bitget_size': p_size,
                            }
                    old_bitget_size = self.positions[p_symbol]['bitget_size']
                    old_gate_size = self.positions[p_symbol]['gate_size']

                    async with self.lock:
                        if exchange.id == 'bitget':
                            self.positions[p_symbol]['bitget_size'] = p_size
                        elif exchange.id == 'gateio':
                            self.positions[p_symbol]['gate_size'] = p_size
                        else:
                            adl_log(f"Unknown exchange id: {exchange.id}")
                            sys.exit(1)

                    if exchange.id == 'bitget':
                        if old_bitget_size != p_size:
                            adl_log(f"Bitget position changed for {p_symbol}: {old_bitget_size} -> {p_size}")
                            try_this(self.check_position_change, params={'symbol': p_symbol}, log_func=adl_log, retries=5, delay=1)
                        self.positions[p_symbol]['bitget_size'] = p_size
                    elif exchange.id == 'gateio':
                        if old_gate_size != p_size:
                            adl_log(f"GateIO position changed for {p_symbol}: {old_gate_size} -> {p_size}")
                            try_this(self.check_position_change, params={'symbol': p_symbol}, log_func=adl_log, retries=5, delay=1)
                    else:
                        adl_log(f"Unknown exchange id: {exchange.id}")
                        sys.exit(1)
                self.error_count = self.error_count - 1 if self.error_count > 1 else 0

            except Exception as e:
                self.error_count += 1
                adl_log(f"Lỗi khi sync: {e}")
                time.sleep(1)

    async def main(self):

        with open(f"{root_path}/code/_settings/futures_symbols.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        symbols = [line.strip() + "/USDT:USDT" for line in lines if line.strip()]
        print(f"Start with symbols size: {len(symbols)}")
        await asyncio.gather(
            self.sync_hedge(self.gate_pro, symbols),
            self.sync_hedge(self.bitget_pro, symbols),
        )

if __name__ == '__main__':
    exchange_manager = ExchangeManager(exchange1, exchange2)
    adl_controller = ADLController(exchange_manager)
    asyncio.run(adl_controller.main())