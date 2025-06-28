import ccxt

import Config

binance_exchange = ccxt.binanceusdm({
    'apiKey': Config.binance_api_key,
    'secret': Config.binance_api_secret,
    'enableRateLimit': True,
})

bitget_exchange = ccxt.bitget({
    'apiKey': Config.bitget_api_key,
    'secret': Config.bitget_api_secret,
    'password': Config.bitget_password,
    'enableRateLimit': True,
})
bitget_exchange.options['defaultType'] = 'swap'

gate_exchange = ccxt.gateio({
    'apiKey': Config.gate_api_key,
    'secret': Config.gate_api_secret,
    'enableRateLimit': True,
})
gate_exchange.options['defaultType'] = 'swap'

okx_exchange = ccxt.okx({
    'apiKey': Config.okx_api_key,
    'secret': Config.okx_api_secret,
    'password': Config.okx_password,
    'enableRateLimit': True,
})
okx_exchange.options['defaultType'] = 'swap'