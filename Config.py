import json

NULL = None

from Define import exchange_file_path, transfer_info_path, balance_info_path

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


with open(transfer_info_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

binance_deposit_address = data.get('binance', {}).get('address', '')
binance_deposit_chain = data.get('binance', {}).get('chain', '')
binance_deposit_network = data.get('bitget', {}).get('network', '')

bitget_deposit_address = data.get('bitget', {}).get('address', '')
bitget_deposit_chain = data.get('bitget', {}).get('chain', '')
bitget_deposit_network = data.get('bitget', {}).get('network', '')

gate_deposit_address = data.get('gate', {}).get('address', '')
gate_deposit_chain = data.get('gate', {}).get('chain', '')
gate_deposit_network = data.get('gate', {}).get('network', '')

keys = [
    ('binance_deposit_address', binance_deposit_address),
    ('binance_deposit_chain', binance_deposit_chain),
    ('binance_deposit_network', binance_deposit_network),
    ('bitget_deposit_address', bitget_deposit_address),
    ('bitget_deposit_chain', bitget_deposit_chain),
    ('bitget_deposit_network', bitget_deposit_network),
    ('gate_deposit_address', gate_deposit_address),
    ('gate_deposit_chain', gate_deposit_chain),
    ('gate_deposit_network', gate_deposit_network),
]
empty = [k for k, v in keys if not v]
if empty:
    raise ValueError(f"Missing deposit information: {', '.join(empty)}")

print("TRANSFER INFO:")
print(f"Binance Deposit Address: {binance_deposit_address}")
print(f"Binance Deposit Chain: {binance_deposit_chain}")
print(f"Binance Deposit Network: {binance_deposit_network}")
print(f"Bitget Deposit Address: {bitget_deposit_address}")
print(f"Bitget Deposit Chain: {bitget_deposit_chain}")
print(f"Bitget Deposit Network: {bitget_deposit_network}")
print(f"Gate Deposit Address: {gate_deposit_address}")
print(f"Gate Deposit Chain: {gate_deposit_chain}")
print(f"Gate Deposit Network: {gate_deposit_network}")

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

gate_deposit_info = {
    "address": gate_deposit_address,
    "chain": gate_deposit_chain,
    "network": gate_deposit_network
}

with open(balance_info_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
max_diff_rate = data.get('max_diff_rate', 0)
print(f"Max difference rate: {max_diff_rate}")
if not (0 < max_diff_rate < 100):
    raise ValueError(f"Invalid max_diff_rate: {max_diff_rate}. It must be between 0 and 1.")
max_diff_rate = float(max_diff_rate)/100
