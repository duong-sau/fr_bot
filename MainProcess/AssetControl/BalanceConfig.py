import json

from Define import balance_info_path

with open(balance_info_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
max_diff_rate = data.get('max_diff_rate', 0)
print(f"Max difference rate: {max_diff_rate}")
if not (0 < max_diff_rate < 100):
    raise ValueError(f"Invalid max_diff_rate: {max_diff_rate}. It must be between 0 and 1.")
max_diff_rate = float(max_diff_rate)/100