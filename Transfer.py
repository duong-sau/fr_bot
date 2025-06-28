import os.path
import sys
import time

import ccxt

import Config
from Config import bitget_deposit_info, binance_deposit_info
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../Core")))

from Core.Define import EXCHANGE
from Define import tunel_log_path, transfer_done_file
from Tool import try_this, write_log


bitget = ccxt.bitget({
            'apiKey': Config.bitget_api_key,
            'secret': Config.bitget_api_secret,
            'password': Config.bitget_password,
            'enableRateLimit': True,
        })


binance = ccxt.binance({
            'apiKey': Config.binance_api_key,
            'secret': Config.binance_api_secret,
            'enableRateLimit': True,
        })

start_time = time.time()

def tunel_log(message):
    log_file = os.path.join(tunel_log_path, f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(start_time))}.log")
    write_log(message, log_file)

def transfer_swap_to_spot(exchange, amount):
    if exchange == EXCHANGE.BINANCE:
        transfer = binance.transfer(code='USDT', amount=amount, fromAccount='swap', toAccount='spot')
        tunel_log(transfer)
    elif exchange == EXCHANGE.BITGET:
        transfer = bitget.transfer(code='USDT', amount=amount, fromAccount='swap', toAccount='spot')
        tunel_log(transfer)
    else:
        raise ValueError("Unsupported exchange for transfer to spot account.")

def with_draw_from_spot(exchange, amount):
    if exchange == EXCHANGE.BINANCE:
        withdraw = binance.withdraw(code='USDT', amount=amount, address=bitget_deposit_info['address'],
                                    params={'chain': bitget_deposit_info['chain'], 'network': bitget_deposit_info['network']})
        tunel_log(withdraw)
        return withdraw['id']
    elif exchange == EXCHANGE.BITGET:
        withdraw = bitget.withdraw(code='USDT', amount=amount, address=Config.binance_deposit_info['address'],
                                   params={'chain': binance_deposit_info['chain'], 'network': Config.binance_deposit_info['network']})
        tunel_log(withdraw)
        return withdraw['id']
    else:
        raise ValueError("Unsupported exchange for withdrawal from spot account.")

def get_withdrawal_txid(exchange, order_id):
    """
    Get the transaction ID of a withdrawal by its order ID.

    :param exchange: The exchange to fetch the withdrawal from.
    :param order_id: The order ID of the withdrawal.
    :return: The transaction ID if found, otherwise None.
    """
    if exchange == EXCHANGE.BINANCE:
        withdrawals = binance.fetchWithdrawals(code='USDT', params={'limit': 10})
    elif exchange == EXCHANGE.BITGET:
        withdrawals = bitget.fetchWithdrawals(code='USDT', params={'limit': 10})
    else:
        raise ValueError("Unsupported exchange for fetching withdrawal txid.")

    for item in withdrawals:
        if item['id'] == order_id:
            if item.get('status') == 'pending':
                raise Exception("withdrawal is still pending, please wait.")
            if item.get('txid', None) is None:
                raise Exception("withdrawal txid is not available yet, please wait.")
            return item.get('txid', None)
    raise Exception("Withdrawal with the given order ID not found.")

def get_withdraw_txid(order_id):
    """
    Get the transaction ID of a withdrawal by its order ID.

    :param order_id: The order ID of the withdrawal.
    :return: The transaction ID if found, otherwise None.
    """
    try:
        withdrawal = bitget.fetchWithdrawals(code='USDT', params={'limit': 10})
        if not withdrawal:
            raise Exception("No withdrawal found with the given order ID.")
        for item in withdrawal:
            if item['id'] == order_id:
                return item.get('txid', None)
        raise Exception("Withdrawal with the given order ID not found.")
    except Exception as e:
        raise Exception(f"Error fetching withdrawal txid: {e}")

def wait_for_desposit(exchange, txid):
    """
    Chờ đợi giao dịch nạp tiền thành công trên Bitget.

    :param exchange: Sàn giao dịch để theo dõi giao dịch nạp tiền.
    :param txid: Mã giao dịch cần theo dõi.
    """
    try:
        if exchange == EXCHANGE.BINANCE:
            deposits = binance.fetchDeposits(code='USDT', limit=10, params={'network': binance_deposit_info['network']})
        elif exchange == EXCHANGE.BITGET:
            deposits = bitget.fetchDeposits(code='USDT', limit=10, params={'network': bitget_deposit_info['network']})
        else:
            raise ValueError("Unsupported exchange for waiting deposit.")
        for deposit in deposits:
            if deposit['txid'] == txid:
                return True

        raise Exception(f"Deposit with txid {txid} not found.")
    except Exception as e:
        raise Exception(f"Error fetching deposits: {e}")

def transfer_spot_to_swap(exchange, amount):
    """
    Chuyển tiền từ tài khoản spot sang tài khoản swap trên sàn giao dịch.

    :param exchange: Sàn giao dịch để thực hiện chuyển tiền.
    :param amount: Số lượng tiền cần chuyển.
    """
    if exchange == EXCHANGE.BINANCE:
        transfer = binance.transfer(code='USDT', amount=amount, fromAccount='spot', toAccount='swap')
        tunel_log(transfer)
    elif exchange == EXCHANGE.BITGET:
        transfer = bitget.transfer(code='USDT', amount=amount, fromAccount='spot', toAccount='swap')
        tunel_log(transfer)
    else:
        raise ValueError("Unsupported exchange for transfer to swap account.")


def transfer_tunel(from_exchange, to_exchange, amount):
    """
    Chuyển tiền từ tài khoản swap của sàn giao dịch này sang tài khoản swap của sàn giao dịch khác.

    :param from_exchange: Sàn giao dịch nguồn để thực hiện chuyển tiền.
    :param to_exchange: Sàn giao dịch đích để nhận tiền.
    :param amount: Số lượng tiền cần chuyển.
    """

    try:
        # wap to spot
        try_this(transfer_swap_to_spot, params={'exchange': from_exchange, 'amount': amount}, log_func=tunel_log, retries=5, delay=5)

        # Withdraw from spot to other exchange
        time.sleep(3)
        client_id = try_this(with_draw_from_spot, params={'exchange': from_exchange, 'amount': amount}, log_func=tunel_log, retries=5, delay=5)

        # deposit to spot
        time.sleep(30)
        txid = try_this(get_withdrawal_txid, params={'exchange': from_exchange, 'order_id': client_id}, log_func=tunel_log, retries=30, delay=10)
        try_this(wait_for_desposit, params={'exchange': to_exchange, 'txid': txid}, log_func=tunel_log, retries=30, delay=10)

        # Transfer from spot to swap
        time.sleep(30)
        try_this(transfer_spot_to_swap, params={'exchange': to_exchange, 'amount': amount}, log_func=tunel_log, retries=5, delay=5)
        write_transfer_status(True)
    except Exception as e:
        tunel_log(f"Transfer failed, {e}")
        write_transfer_status(False)
        raise

def write_transfer_status(bOk):
    with open(transfer_done_file, 'w+', encoding='utf-8') as f:
        if bOk:
            f.write('OK\n')
        else:
            f.write('ERROR\n')

if __name__ == '__main__':
    # Example usage
    if len(sys.argv) < 4:
        print("Usage: python Transfer.py <from_exchange> <to_exchange> <amount>")
        sys.exit(1)
    f_exchange = sys.argv[1]
    if f_exchange == 'binance':
        from_exchange = EXCHANGE.BINANCE
    elif f_exchange == 'bitget':
        from_exchange = EXCHANGE.BITGET
    else:
        raise ValueError("Unsupported exchange. Use 'binance' or 'bitget'.")

    t_exchange = sys.argv[2]
    if t_exchange == 'binance':
        to_exchange = EXCHANGE.BINANCE
    elif t_exchange == 'bitget':
        to_exchange = EXCHANGE.BITGET
    else:
        raise ValueError("Unsupported exchange. Use 'binance' or 'bitget'.")

    amount = float(sys.argv[3])
    transfer_tunel(from_exchange, to_exchange, amount)
