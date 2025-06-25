import Config
from Core.Define import PositionSide, Position, EXCHANGE
from Tracker.Tracker import AccountBalance


class OKXTracker:
    def __init__(self):
        import ccxt
        self.client = ccxt.okx({
            'apiKey': Config.okx_api_key,
            'secret': Config.okx_api_secret,
            'password': Config.okx_password,
            'enableRateLimit': True,
        })
        self.client.options['defaultType'] = 'swap'
    def get_open_positions(self):
        """

        :return:
        """
        positions = []
        response = self.client.fetch_positions()
        positions_json = [pos for pos in response ]
        for pos in positions_json:
            symbol = pos['info']['instId'].replace('-USDT-SWAP', 'USDT').replace('-', '')
            side = PositionSide.LONG if pos['side'].upper() == 'LONG' else PositionSide.SHORT
            margin= float(pos['info']['im']) if 'im' in pos['info'] else 1.0  # Default to 1.0 if not available
            position = Position(symbol=symbol, side=side, amount=float(pos['contracts']),
                                entry_price=float(pos['entryPrice']), exchange=EXCHANGE.OKX, margin=margin)
            positions.append(position)
        return positions
    def get_cross_margin_account_info(self):
        """
        Fetch cross margin account information and calculate ROI for each asset.
        :return:
        """
        account_info = self.client.fetchBalance()
        info = account_info['info']
        total_margin_balance = float(info['margin_balance'])
        total_initial_margin = float(info['initial_margin'])
        total_maint_margin = float(info['maint_margin'])
        available_balance = float(info['available_balance'])
        unrealized_pnl = float(info['unrealized_pnl'])

        account_balance = AccountBalance(total_margin_balance,
                                         total_initial_margin,
                                         total_maint_margin,
                                         available_balance,
                                         unrealized_pnl)
        return account_balance

    def get_current_funding_rate(self, symbol):
        """
        Get the current funding rate for a given symbol.

        :param symbol: The trading pair symbol (e.g., 'BTC/USDT')
        :return: Current funding rate as a float
        """
        symbol = symbol.replace('USDT', '-USDT-SWAP').replace('/', '-')
        funding_rate = self.client.fetchFundingRate(symbol)
        funding_rate = float(funding_rate['fundingRate']) * 100
        funding_rate = round(funding_rate, 4)
        return funding_rate