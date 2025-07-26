import ccxt
import ccxt.pro
import Config

from Define import exchange1, exchange2
Config.load_config(exchange1, exchange2)

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

bitget_pro = ccxt.pro.bitget({
    'apiKey': Config.bitget_api_key,
    'secret': Config.bitget_api_secret,
    'password': Config.bitget_password,
    'options': {'defaultType': 'swap'}
})
gate_pro = ccxt.pro.gateio({
    'apiKey': Config.gate_api_key,
    'secret': Config.gate_api_secret,
    'uid': "22397301",
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'
    }
})
