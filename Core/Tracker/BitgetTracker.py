import time

from Core.Define import PositionSide, Position, EXCHANGE
from Core.Tracker.Tracker import AccountBalance


class BitgetTracker:

    def __init__(self, exchange):
            self.client = exchange

    def get_open_positions(self):
        """
        Get all currently open positions on BitGet Futures.
        :return: List of open positions (Position objects)
        """

        positions = []
        response = self.client.fetch_positions()
        positions_json = [pos for pos in response]
        for pos in positions_json:
            side = PositionSide.LONG if pos['side'].upper() == 'LONG' else PositionSide.SHORT
            leverage = 1 / float(pos['initialMarginPercentage'])
            symbol = pos['info']['symbol']
            position = Position(symbol=pos['info']['symbol'], side=side, amount=float(pos['contracts']),
                                entry_price=float(pos['entryPrice']), exchange=EXCHANGE.BITGET, margin=leverage)

            # total_paid_funding = self.get_paid_funding(symbol, pos['timestamp'])
            total_paid_funding = float(pos['info'].get('totalFee', 0.0))
            position.set_paid_funding(total_paid_funding)

            positions.append(position)
        return positions
    def get_cross_margin_account_info(self):
        """
        Fetch cross margin account information and calculate ROI for each asset.
        :return:
        """
        params = {'productType': 'USDT-FUTURES'}
        account_info = self.client.fetchBalance(params)
        info = account_info['info'][0]
        total_margin_balance = float(info['unionTotalMargin'])
        total_initial_margin = float(info['accountEquity'])
        total_maint_margin = float(info['accountEquity'])
        available_balance = float(info['available'])
        unrealized_pnl = float(info['unrealizedPL'])

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

        while True:
            try:
                funding_history = self.client.fetchFundingHistory(
                    symbol=symbol,
                    since=start_time,
                    limit=100,
                    params={
                        'endTime':end_time,
                    }
                )
            except Exception as e:
                print(f"Lỗi lấy funding: {e}")
                break

            if not funding_history:
                break

            # Cộng funding
            for f in funding_history:
                total_paid += float(f.get("amount", 0))

            # Lấy thời gian cuối cùng để tiếp tục
            end_time = funding_history[0].get("timestamp") - 1

            # Chờ nhẹ để tránh bị rate limit
            time.sleep(0.2)

        return total_paid