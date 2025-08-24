"""
Auto Hedge Monitor — Binance + Bitget (Binance: hedge + collateral watcher, Bitget: extra short 15,000)

Behavior:
1) Binance futures:
   - Listen position (stream) và nếu short < target thì market short bù.
   - Collateral watcher: khi USDT futures < lower → vay USDT (Crypto Loan) trên spot và chuyển sang futures.
     Khi > upper → chuyển về spot và repay loan.

2) Bitget futures:
   - Poll positions định kỳ. Nếu short < target thì market short bù.

⚠️ Notes:
- Đặt API keys trong _settings/hedge.json:
  {
    "binance": {"api_key": "...", "api_secret": "..."},
    "bitget":  {"api_key": "...", "api_secret": "...", "passphrase": "..."}
  }
- Kiểm tra account mode (one-way/cross) trên cả hai sàn cho đúng với chiến lược.
- Test với size nhỏ trước khi chạy thật.
"""

import os
import asyncio
import logging
import json
import ccxt.pro as ccxtpro
import ccxt.async_support as ccxt

SYMBOL_PERP_CCXT = 'SXP/USDT:USDT'

# Binance futures collateral thresholds
BINANCE_FUTURES_BALANCE_LOWER = 50.0
BINANCE_FUTURES_BALANCE_UPPER = 100.0

# Target short per exchange
BINANCE_SHORT_QTY = 150  # per exchange
BITGET_SHORT_QTY = 150

POLL_INTERVAL = 30

with open(r'C:\job\dim\fr_bot\code\_settings\hedge.json', 'r') as f:
    hedge_config = json.load(f)

BINANCE_API_KEY = hedge_config['binance']['api_key']
BINANCE_SECRET  = hedge_config['binance']['api_secret']

BITGET_API_KEY   = hedge_config.get('bitget', {}).get('api_key')
BITGET_SECRET    = hedge_config.get('bitget', {}).get('api_secret')
BITGET_PASSPHRASE= hedge_config.get('bitget', {}).get('password')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

async def create_clients():
    # Binance spot (REST) cho loan/transfer
    binance_spot = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })

    # Binance USDT-M futures (Pro WS)
    binance_fut = ccxtpro.binanceusdm({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,
    })
    await binance_fut.load_markets()

    # Bitget USDT-M futures (Pro WS)
    bitget_fut = None

    bitget_fut = ccxtpro.bitget({
        'apiKey': BITGET_API_KEY,
        'secret': BITGET_SECRET,
        'password': BITGET_PASSPHRASE,   # Bitget uses "password" for passphrase in ccxt
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',      # USDT-M perpetuals
            # 'marginMode': 'cross',    # set if needed
            # 'hedgeMode': False,       # Bitget supports One-way/Hedge; ensure it matches your account
        }
    })
    await bitget_fut.load_markets()

    return binance_spot, binance_fut, bitget_fut

async def get_current_short_contracts(ex, symbol: str) -> float:
    """Return absolute short contracts on given symbol (USDT-M perpetual)."""
    try:
        positions = await ex.fetch_positions([symbol])
        short = 0.0
        for p in positions:
            # unified fields; for one-way mode, short is contracts when side is 'short' or negative
            if p.get('symbol') == symbol:
                contracts = float(p.get('contracts') or 0)  # signed size may not be unified across all exchanges
                # Some exchanges give separate long/short entries; to stay safe, sum abs of negative or explicit short
                side = p.get('side')
                if side == 'short':
                    short += abs(contracts)
                else:
                    # fallback: if not side-tagged, infer from signed size
                    if contracts < 0:
                        short += abs(contracts)
        return short
    except Exception as e:
        logging.warning(f"get_current_short_contracts error: {e}")
        return 0.0

async def open_market_short(ex, symbol: str, qty: float):
    """Open market short (sell) with reduceOnly=False to increase short size."""
    try:
        short_qty = await get_current_short_contracts(ex, SYMBOL_PERP_CCXT)
        print(f"Current short contracts: {short_qty}")

        need = round((BITGET_SHORT_QTY - short_qty) / 10) * 10  # align to step 10 to match original logic
        if need <= 0:
            return None

        order = await ex.create_order(symbol, 'market', 'sell', need, params={'reduceOnly': False})
        logging.info(f"[{ex.id}] Opened market short {need} {symbol}")
        return order
    except Exception as e:
        logging.error(f"[{ex.id}] Failed opening short: {e}")
        return None

# -------- Binance helpers --------
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

async def binance_loan_and_transfer(binance_spot, amount_usdt: float):
    try:
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

async def binance_repay_loan(binance_spot, amount_usdt: float):
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

# -------- Tasks --------
async def futures_collateral_watcher(binance_spot, binance_fut):
    while True:
        try:
            avail = await binance_available_futures_usdt(binance_fut)
            logging.info(f"[binance] futures available USDT: {avail:.2f}")
            if avail < BINANCE_FUTURES_BALANCE_LOWER - 20:
                need = BINANCE_FUTURES_BALANCE_UPPER - avail
                need = max(20, need)
                logging.info(f"[binance] Low futures balance: borrowing {need} via crypto loan")
                await binance_loan_and_transfer(binance_spot, need)
            elif avail > BINANCE_FUTURES_BALANCE_UPPER + 20:
                repay_amt = min(avail - BINANCE_FUTURES_BALANCE_UPPER, avail)
                if repay_amt >= 20:
                    logging.info(f"[binance] High futures balance: attempting repay {repay_amt}")
                    await binance_repay_loan(binance_spot, repay_amt)
        except Exception as e:
            logging.error(f"futures_collateral_watcher error: {e}")
        await asyncio.sleep(POLL_INTERVAL)

async def binance_positions_listener_and_rebalancer(binance_fut):
    while True:
        try:
            positions = await binance_fut.watch_positions([SYMBOL_PERP_CCXT])
            short_pos = 0.0
            for p in positions:
                if p.get('symbol') == SYMBOL_PERP_CCXT:
                    # Binance usually provides 'side' too
                    side = p.get('side')
                    contracts = float(p.get('contracts') or 0)
                    if side == 'short' or contracts < 0:
                        short_pos += abs(contracts)
            logging.info(f"[binance] Short position: {short_pos:.2f}")
            if short_pos < BINANCE_SHORT_QTY - 5:
                need = BINANCE_SHORT_QTY - short_pos
                logging.info(f"[binance] Short under target -> opening short {need}")
                await open_market_short(binance_fut, SYMBOL_PERP_CCXT, need)
        except Exception as e:
            logging.error(f"[binance] positions_listener error: {e}")

async def bitget_positions_listener_and_rebalancer(bitget_fut):
    """Bitget WebSocket listener giữ short 15,000."""
    while True:
        try:
            positions = await bitget_fut.watch_positions([SYMBOL_PERP_CCXT])
            short_pos = 0.0
            for p in positions:
                if p.get('symbol') == SYMBOL_PERP_CCXT:
                    side = p.get('side')
                    contracts = float(p.get('contracts') or 0)
                    if side == 'short' or contracts < 0:
                        short_pos += abs(contracts)
            logging.info(f"[bitget] Short position: {short_pos:.2f}")
            if short_pos < BINANCE_SHORT_QTY - 5:
                need = BINANCE_SHORT_QTY - short_pos
                logging.info(f"[bitget] Short under target -> opening short {need}")
                await open_market_short(bitget_fut, SYMBOL_PERP_CCXT, need)
        except Exception as e:
            logging.error(f"[bitget] positions_listener error: {e}")

async def main():
    binance_spot, binance_fut, bitget_fut = await create_clients()

    tasks = [
        # asyncio.create_task(futures_collateral_watcher(binance_spot, binance_fut)),
        asyncio.create_task(binance_positions_listener_and_rebalancer(binance_fut)),
        # asyncio.create_task(bitget_positions_listener_and_rebalancer(bitget_fut)),
    ]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Stopped by user')
