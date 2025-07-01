import json
import sys

from Core.Define import convert_exchange_name_to_exchange, EXCHANGE
from Tool import check_config_empty_by_error
from Define import exchange_file_path

binance_api_key, binance_api_secret = '', ''
bitget_api_key, bitget_api_secret, bitget_password = '', '', ''

bitget_sub_api_key, bitget_sub_api_secret, bitget_sub_password = '', '', ''
gate_api_key, gate_api_secret = '', ''


def load_config(exchange1, exchange2):
    """
    Load configuration for the specified exchanges.
    """
    global binance_api_key, binance_api_secret
    global bitget_api_key, bitget_api_secret, bitget_password
    global bitget_sub_api_key, bitget_sub_api_secret, bitget_sub_password
    global gate_api_key, gate_api_secret
    print(f"Loading configuration for exchanges: {exchange1}, {exchange2}")
    with open(exchange_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if exchange1 == EXCHANGE.BITGET or exchange2 == EXCHANGE.BITGET or exchange1 == EXCHANGE.BITGET_SUB or exchange2 == EXCHANGE.BITGET_SUB:
        bitget_api_key = data.get('bitget', {}).get('api_key', '')
        bitget_api_secret = data.get('bitget', {}).get('api_secret', '')
        bitget_password = data.get('bitget', {}).get('password', '')
        check_config_empty_by_error([bitget_api_key, bitget_api_secret, bitget_password])

    if exchange1 == EXCHANGE.BITGET_SUB or exchange2 == EXCHANGE.BITGET_SUB:
        bitget_sub_api_key = data.get('bitget_sub', {}).get('api_key', '')
        bitget_sub_api_secret = data.get('bitget_sub', {}).get('api_secret', '')
        bitget_sub_password = data.get('bitget_sub', {}).get('password', '')
        check_config_empty_by_error([bitget_sub_api_key, bitget_sub_api_secret, bitget_sub_password])

    if exchange1 == EXCHANGE.BINANCE or exchange2 == EXCHANGE.BINANCE:
        binance_api_key = data.get('binance', {}).get('api_key', '')
        binance_api_secret = data.get('binance', {}).get('api_secret', '')
        check_config_empty_by_error([binance_api_key, binance_api_secret])

    if exchange1 == EXCHANGE.GATE or exchange2 == EXCHANGE.GATE:
        gate_api_key = data.get('gate', {}).get('api_key', '')
        gate_api_secret = data.get('gate', {}).get('api_secret', '')
        check_config_empty_by_error([gate_api_key, gate_api_secret])
