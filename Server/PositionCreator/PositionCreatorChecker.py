import asyncio
import os
import sys
import ccxt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Core.Tool import push_notification
from Define import root_path

symbols = []

file = open(f"{root_path}/code/_settings/futures_symbols.txt", 'r', encoding='utf-8')
lines = file.readlines()
for line in lines:
    symbols.append(line.strip())

print(f"Start with symbols size{len(symbols)}")

gate = ccxt.gate()
bitget = ccxt.bitget()
borrow_info = bitget.public_get_margin_v1_isolated_public_interestRateAndLimit({
    "symbol": "BTCUSDT"
})
print(borrow_info)

rates = {}

def compute_8h_funding_rate(rate, interval=8):
    """
    Compute the 8-hour funding rate from the given rate.
    """
    if interval == '1h':
        g_rate = rate* 8
    elif interval == '2h':
        g_rate = rate * 4
    elif interval == '4h':
        g_rate = rate * 2
    elif interval == '8h':
        g_rate = rate
    else:
        raise ValueError("Unsupported interval. Supported intervals are: 1h, 2h, 4h, 8h.")

    return round(g_rate, 4)


def fetch_funding_rate(exchange, symbol, exchange_name):

        if symbol not in rates:
            rates[symbol] = {'gate': None, 'bitget': None}

        try:
            rate = exchange.fetch_funding_rate(symbol)
            interval  = rate['interval']
            net_fundingrate = rate['fundingRate'] if rate and 'fundingRate' in rate else None
            actual_funding_rate = compute_8h_funding_rate(net_fundingrate, interval) * 100  # Convert to percentage
            rates[symbol][exchange_name] = actual_funding_rate if actual_funding_rate else None

        except Exception as e:
            rates[symbol][exchange_name] = None

async def fetch_all_funding_rates(symbols):
    while True:
        for symbol in symbols:
            print(f"Fetching funding rate for symbol: {symbol}")
            symbol = symbol + "/USDT:USDT"
            fetch_funding_rate(gate, symbol, "gate")
            fetch_funding_rate(bitget, symbol, "bitget")
            print(f"Updated funding rate for symbol :{symbol}", f"rate: {rates[symbol]}")
            await asyncio.sleep(0.2)

potential_symbols = []

def entry_potential(symbol):
    with open(f"{root_path}/data/futures_symbols.txt", 'w', encoding='utf-8') as f:
        for s in potential_symbols:
            f.write(s + '\n')
    import subprocess
    subprocess.Popen(
        ['python', f'{root_path}/code/MainProcess/PositionCreator/PotentialChecker.py', symbol],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

async def main():
    task  = asyncio.create_task(fetch_all_funding_rates(symbols))
    threshold_in = 0.12
    threshold_out = 0.08
    while True:
        for symbol, rate in rates.items():
            gate_rate = rate['gate']
            bitget_rate = rate['bitget']

            if gate_rate is not None and bitget_rate is not None:
                if symbol not in potential_symbols:
                    if bitget_rate - gate_rate > threshold_in:
                        potential_symbols.append(symbol)
                        entry_potential(symbol)
                        push_notification(f'New potetial {symbol}, Gate Rate: {gate_rate}, Bitget Rate: {bitget_rate}')
                        print(f"Potential arbitrage opportunity found for {symbol}: Gate Rate: {gate_rate}, Bitget Rate: {bitget_rate}")
                else:
                    if bitget_rate - gate_rate <= threshold_out:
                        potential_symbols.remove(symbol)
                        print(f"Removed {symbol} from potential arbitrage opportunities.")

        await asyncio.sleep(2)
    await task
if __name__ == '__main__':
    asyncio.run(main())