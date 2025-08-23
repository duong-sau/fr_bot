"""
Auto Hedge Monitor — Binance Only (100% short on Binance)

Behavior:
1) **Listen position** on Binance futures only. If the short hedge position drops below the target notional, the bot will open a market short to restore the target.

2) **Binance futures collateral watcher:** periodically checks the Binance futures wallet. If the available futures USDT falls below a configured threshold, the bot will borrow USDT (margin loan) and transfer to futures. If the available futures USDT rises above an upper threshold, the bot will try to repay outstanding margin.

⚠️ Notes:
- Set API keys in environment variables.
- Adjust endpoints for your account type (cross/isolated).
- Test carefully with small amounts.
"""

import os
import asyncio
import logging
import sys

import ccxt.pro as ccxtpro
import ccxt.async_support as ccxt

SYMBOL_PERP_CCXT = 'SXP/USDT:USDT'

BINANCE_FUTURES_BALANCE_LOWER = 50.0
BINANCE_FUTURES_BALANCE_UPPER = 100.0

FIXED_SHORT_QTY = 15000  # fixed quantity for shorts

POLL_INTERVAL = 30

import json

with open('_settings/hedge.json', 'r') as f:
    hedge_config = json.load(f)
BINANCE_API_KEY = hedge_config['binance']['api_key']
BINANCE_SECRET = hedge_config['binance']['api_secret']
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

async def create_client():
    binance_spot = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })

    binance_fut = ccxtpro.binanceusdm({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,
    })

    return binance_spot, binance_fut

async def open_market_short(ex, symbol):
    try:
        positions = await ex.fetch_positions([symbol])
        current_short = 0.0
        for p in positions:
            if p.get('symbol') == symbol:
                current_short += abs(float(p.get('contracts') or 0))
        logging.info(f"Current short position on {symbol}: {current_short:.4f}")
        need = round((FIXED_SHORT_QTY - current_short)/10)*10
        order = await ex.create_order(symbol, 'market', 'sell', need)
        logging.info(f"Opened market short {need:.4f} {symbol}")
        return order
    except Exception as e:
        logging.error(f"Failed opening short: {e}")
        return None

async def binance_available_futures_usdt(binance_fut):
    try:
        bal = await binance_fut.fetch_balance()
        info = bal.get('info', {})
        futures_balance = 0.0
        if 'assets' in info:
            for a in info['assets']:
                if a.get('asset') == 'USDT':
                    futures_balance = float(a.get('availableBalance') or a.get('walletBalance') or 0)
        else:
            futures_balance = float(bal.get('free', {}).get('USDT', 0) or 0)
        return futures_balance
    except Exception as e:
        logging.warning(f"fetch futures balance error: {e}")
        return 0.0

async def binance_loan_and_transfer(binance_spot, amount_usdt):
    pass
    try:
        # borrow via crypto loan API
        amount_usdt = round(amount_usdt)
        params = {'loanCoin': 'USDT', 'loanAmount': amount_usdt, 'collateralCoin': 'SXP'}
        res = await binance_spot.sapiv2_post_loan_flexible_borrow(params)
        logging.info(f"Borrowed {amount_usdt} USDT via crypto loan: {res}")
        await binance_spot.sapi_post_futures_transfer({'asset': 'USDT', 'amount': str(amount_usdt), 'type': 1})
        logging.info(f"Transferred {amount_usdt} USDT spot->futures")
        return True
    except Exception as e:
        logging.error(f"Crypto loan borrow/transfer failed: {e}")
        return False

async def binance_repay_loan(binance_spot, amount_usdt):
    try:
        amount_usdt = round(amount_usdt)
        await binance_spot.sapi_post_futures_transfer({'asset': 'USDT', 'amount': str(amount_usdt), 'type': 2})
        logging.info(f"Transferred {amount_usdt} USDT futures->spot")

        await asyncio.sleep(5)

        params = {'loanCoin': 'USDT', 'repayAmount': amount_usdt, 'collateralCoin': 'SXP'}
        res = await binance_spot.sapiv2_post_loan_flexible_repay(params)
        logging.info(f"Repaid crypto loan {amount_usdt}: {res}")
        return True
    except Exception as e:
        logging.error(f"Crypto loan repay failed: {e}")
        return False

async def futures_collateral_watcher(binance_spot, binance_fut):
    while True:
        try:
            avail = await binance_available_futures_usdt(binance_fut)
            logging.info(f"Binance futures available USDT: {avail:.2f}")
            if avail < BINANCE_FUTURES_BALANCE_LOWER - 20:
                need = BINANCE_FUTURES_BALANCE_UPPER - avail
                need = max(20, need)
                logging.info(f"Low futures balance: borrowing {need} via crypto loan")
                await binance_loan_and_transfer(binance_spot, need)
            elif avail > BINANCE_FUTURES_BALANCE_UPPER + 20:
                repay_amt = min(avail - BINANCE_FUTURES_BALANCE_UPPER, avail)
                if repay_amt >= 20:
                    logging.info(f"High futures balance: attempting repay {repay_amt}")
                    await binance_repay_loan(binance_spot, repay_amt)
        except Exception as e:
            logging.error(f"futures_collateral_watcher error: {e}")
        await asyncio.sleep(POLL_INTERVAL)

async def positions_listener_and_rebalancer(binance_fut):
    while True:
        try:
            positions = await binance_fut.watch_positions([SYMBOL_PERP_CCXT])
            short_pos = 0.0
            for p in positions:
                if p.get('symbol') == SYMBOL_PERP_CCXT:
                    short_pos += abs(float(p.get('contracts') or 0))
            logging.info(f"Short position - Binance: {short_pos:.2f}")
            if short_pos < FIXED_SHORT_QTY - 5:
                logging.info(f"Short under target -> opening short {FIXED_SHORT_QTY}")
                await open_market_short(binance_fut, SYMBOL_PERP_CCXT)
        except Exception as e:
            logging.error(f"positions_listener error: {e}")


async def main():
    binance_spot, binance_fut = await create_client()
    tasks = [
        asyncio.create_task(futures_collateral_watcher(binance_spot, binance_fut)),
        asyncio.create_task(positions_listener_and_rebalancer(binance_fut)),
    ]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Stopped by user')
