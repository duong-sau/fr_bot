import ccxt
import ccxt.pro
import Config

from Core.Define import EXCHANGE

class ExchangeManager:
    def __init__(self, exchange1: EXCHANGE, exchange2: EXCHANGE):
        Config.load_config(exchange1, exchange2)

        self.binance_exchange = ccxt.binanceusdm({
            'apiKey': Config.binance_api_key,
            'secret': Config.binance_api_secret,
            'enableRateLimit': True,
        })

        self.bitget_exchange = ccxt.bitget({
            'apiKey': Config.bitget_api_key,
            'secret': Config.bitget_api_secret,
            'password': Config.bitget_password,
            'enableRateLimit': True,
        })
        self.bitget_exchange.options['defaultType'] = 'swap'

        self.gate_exchange = ccxt.gateio({
            'apiKey': Config.gate_api_key,
            'secret': Config.gate_api_secret,
            'enableRateLimit': True,
        })
        self.gate_exchange.options['defaultType'] = 'swap'

        self.bitget_pro = ccxt.pro.bitget({
            'apiKey': Config.bitget_api_key,
            'secret': Config.bitget_api_secret,
            'password': Config.bitget_password,
            'options': {'defaultType': 'swap'}
        })

        self.gate_pro = ccxt.pro.gateio({
            'apiKey': Config.gate_api_key,
            'secret': Config.gate_api_secret,
            'uid': "22397301",
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap'
            }
        })