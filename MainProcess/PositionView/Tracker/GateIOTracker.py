from Core.Define import PositionSide, Position, EXCHANGE
from Core.Exchange import Exchange
from MainProcess.PositionView.Tracker.Tracker import AccountBalance


class GateIOTracker:
    def __init__(self):
       self.client = Exchange.gate_exchange

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
            margin = float(pos['maintenanceMargin']) if 'maintenanceMargin' in pos else 1.0  # Default to 1.0 if not available
            position = Position(symbol=symbol, side=side, amount=float(pos['contracts']),
                                entry_price=float(pos['entryPrice']), exchange=EXCHANGE.GATE, margin=margin)
            positions.append(position)

            total_paid_funding = self.get_paid_funding(symbol, pos['timestamp'])
            position.set_paid_funding(total_paid_funding)

        return positions
    def get_cross_margin_account_info(self):
        """
        Fetch cross margin account information and calculate ROI for each asset.
        :return:
        """
        account_info = self.client.fetchBalance()
        info = account_info['info'][0]
        total_margin_balance = float(info['available']) + float(info['position_initial_margin'])
        total_initial_margin = float(info['position_initial_margin'])
        total_maint_margin = float(info['maintenance_margin'])
        available_balance = float(info['available'])
        unrealized_pnl = float(info['unrealised_pnl'])

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
    def get_paid_funding(self, symbol, start_time):
        """
        Get the total funding paid for a given symbol.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').

        Returns:
            The total funding paid as a float.
        """
        try:
            funding_history = self.client.fetchFundingHistory(symbol=symbol, since=start_time, limit=100)
            total_paid = sum(float(funding['amount']) for funding in funding_history)
            return total_paid
        except Exception as e:
            print(f"Error fetching funding history for {symbol}: {e}")
            return 0.0