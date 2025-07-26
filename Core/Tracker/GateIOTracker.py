from Core.Define import PositionSide, Position, EXCHANGE
from Core.Tracker.Tracker import AccountBalance


class GateIOTracker:
    def __init__(self, exchange):
       self.client = exchange

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
