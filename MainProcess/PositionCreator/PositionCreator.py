import asyncio
import time

import ccxt

symbols = [
    "ZRC", "LAUNCHCOIN", "DMC", "USUAL", "CKB", "ZRO", "VVV", "BID",
    "BADGER", "PARTI", "RARE", "KOMA", "ZEREBRO", "RESOLV", "COTI",
    "XAUT", "OM", "GPS"
]

more_crypto_symbols = [
    "BSW", "MYRO", "VINE", "TUT", "AUDIO", "MILK", "IMX", "NIL",
    "APE", "KAITO", "FHE", "TANSSI", "IDOL", "SNT", "LISTA",
    "BERA", "GRIFFAIN", "SXT"
]
extra_crypto_symbols = [
    "LOOKS", "DYM", "SKYAI", "TA", "USDC", "SPX", "AGT", "C98",
    "DRIFT", "RUNE", "EIGEN", "AIN", "VIRTUAL", "VELVET", "KNC",
    "AMP", "TIA", "PIPPIN"
]
symbols.extend(more_crypto_symbols)
symbols.extend(extra_crypto_symbols)

symbols = [symbol + "/USDT:USDT" for symbol in symbols]

gate = ccxt.gate()
bitget = ccxt.bitget()

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
            fetch_funding_rate(gate, symbol, "gate")
            fetch_funding_rate(bitget, symbol, "bitget")
            print(f"Updated funding rate for symbol :{symbol}", f"rate: {rates[symbol]}")
            await asyncio.sleep(2)

potential_symbols = []

def entry_potential(symbol):
    print(f"Potential arbitrage opportunity found for {symbol}")
    import subprocess
    subprocess.Popen(['python', 'PotentialChecker.py', symbol])

async def main():
    task  = asyncio.create_task(fetch_all_funding_rates(symbols))
    threshold = 0.2
    while True:
        for symbol, rate in rates.items():
            gate_rate = rate['gate']
            bitget_rate = rate['bitget']

            if gate_rate is not None and bitget_rate is not None:
                if symbol not in potential_symbols:
                    if bitget_rate - gate_rate > threshold:
                        potential_symbols.append(symbol)
                        entry_potential(symbol)
                        print(f"Potential arbitrage opportunity found for {symbol}: Gate Rate: {gate_rate}, Bitget Rate: {bitget_rate}")
                else:
                    if bitget_rate - gate_rate <= threshold:
                        potential_symbols.remove(symbol)
                        print(f"Removed {symbol} from potential arbitrage opportunities.")

        await asyncio.sleep(2)
    await task
if __name__ == '__main__':
    asyncio.run(main())