import time

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
            # total_paid_funding = self.get_paid_funding(symbol, pos['timestamp'])
            if symbol.startswith("SXP"):
                continue
            total_paid_funding = float(pos['info'].get('pnl_fund', 0.0))
            position.set_paid_funding(total_paid_funding)

        return positions
    def get_cross_margin_account_info(self):
        """
        Fetch cross margin account information and calculate ROI for each asset.
        :return:
        """
        account_info = self.client.fetchBalance(params={'unifiedAccount': True})
        info = account_info['info'][0]
        total_margin_balance = float(info['unified_account_total_equity'])
        total_initial_margin = 0
        total_maint_margin =0
        available_balance = 0
        unrealized_pnl = 0

        account_balance = AccountBalance(total_margin_balance,
                                         total_initial_margin,
                                         total_maint_margin,
                                         available_balance,
                                         unrealized_pnl)
        return account_balance

    def get_paid_funding(self, symbol, start_time):
        """
        Lấy tổng funding đã trả từ start_time cho đến hiện tại.
        """
        total_paid = 0.0
        end_time = self.client.milliseconds()
        symbol = symbol.replace('USDT', '_USDT')
        while True:
            try:
                funding_history = self.client.fetchFundingHistory(
                    symbol=symbol,
                    since=start_time,
                    limit=100,
                    end_time=end_time,
                    params={
                        'endTime': end_time,
                    }
                )
            except Exception as e:
                print(f"Lỗi lấy funding: {e}")
                break

            if not funding_history:
                break

            # Cộng funding
            out = False
            for f in funding_history:
                if f.get('timestamp', 0) < start_time:
                    out = True
                    break
                if f.get('timestamp', 0) > end_time:
                    out = True
                    break
                total_paid += float(f.get("amount", 0))
            if out:
                break

            # Lấy thời gian cuối cùng để tiếp tục
            end_time = funding_history[0].get("timestamp") - 1

            # Chờ nhẹ để tránh bị rate limit
            time.sleep(0.2)

        return total_paid