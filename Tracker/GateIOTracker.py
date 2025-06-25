import Config
from Core.Define import PositionSide, Position, EXCHANGE
from Tracker.Tracker import AccountBalance


class GateIOTracker:
    def __init__(self):
        """
        Initialize the Tracker with a ccxt GateIO client.
        """
        import ccxt
        self.client = ccxt.gateio({
            'apiKey': Config.gate_api_key,
            'secret': Config.gate_api_secret,
            'enableRateLimit': True,
        })
        self.client.options['defaultType'] = 'swap'
    def get_open_positions(self):
        """
        Get all currently open positions on GateIO Futures.
        :return:
        """
        positions = []
        response = self.client.fetch_positions()
        positions_json = [pos for pos in response if float(pos['contracts']) > 0]
        for pos in positions_json:
            symbol = pos['info']['contract'].replace('_', '')
            side = PositionSide.LONG if pos['side'].upper() == 'LONG' else PositionSide.SHORT
            margin = float(pos['initialMargin']) if 'initialMargin' in pos else 1.0  # Default to 1.0 if not available
            position = Position(symbol=symbol, side=side, amount=float(pos['contracts']),
                                entry_price=float(pos['entryPrice']), exchange=EXCHANGE.GATE, margin=margin)
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
        :param symbol:
        :return:
        """
        symbol = symbol.replace('USDT', '_USDT')
        funding_rate = self.client.fetchFundingRate(symbol)
        funding_rate = float(funding_rate['fundingRate']) * 100
        funding_rate = round(funding_rate, 4)
        return funding_rate