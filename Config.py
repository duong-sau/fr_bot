import json

from Define import exchange_file_path

with open(exchange_file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

binance_api_key = data.get('binance', {}).get('api_key', '')
binance_api_secret = data.get('binance', {}).get('api_secret', '')
bitget_api_key = data.get('bitget', {}).get('api_key', '')
bitget_api_secret = data.get('bitget', {}).get('api_secret', '')
bitget_password = data.get('bitget', {}).get('password', '')
okx_api_key = data.get('okx', {}).get('api_key', '')
okx_api_secret = data.get('okx', {}).get('api_secret', '')
okx_password = data.get('okx', {}).get('password', '')
gate_api_key = data.get('gate', {}).get('api_key', '')
gate_api_secret = data.get('gate', {}).get('api_secret', '')



keys = [
    ('binance_api_key', binance_api_key),
    ('binance_api_secret', binance_api_secret),
    ('bitget_api_key', bitget_api_key),
    ('bitget_api_secret', bitget_api_secret),
    ('bitget_password', bitget_password),
    ('okx_api_key', okx_api_key),
    ('okx_api_secret', okx_api_secret),
    ('okx_password', okx_password),
    ('gate_api_key', gate_api_key),
    ('gate_api_secret', gate_api_secret),
]
empty = [k for k, v in keys if not v]

if empty:
    raise ValueError(f"Missing API keys: {', '.join(empty)}")

binance_deposit_address = data.get('binance', {}).get('address', '')
binance_deposit_chain = data.get('binance', {}).get('chain', '')
binance_deposit_network = data.get('bitget', {}).get('address', '')

bitget_deposit_address = data.get('bitget', {}).get('address', '')
bitget_deposit_chain = data.get('bitget', {}).get('chain', '')
bitget_deposit_network = data.get('bitget', {}).get('network', '')

binance_deposit_info = {
    "address": binance_deposit_address,
    "chain": binance_deposit_chain,
    "network": binance_deposit_network
}

bitget_deposit_info = {
    "address": bitget_deposit_address,
    "chain": bitget_deposit_chain,
    "network": bitget_deposit_network
}