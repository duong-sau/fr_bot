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
            side = PositionSide.LONG if str(pos.get('side', '')).upper() == 'LONG' else PositionSide.SHORT
            # Derive leverage safely
            try:
                imp = pos.get('initialMarginPercentage')
                leverage = 1.0 / float(imp) if imp not in (None, '', 0, '0') else 0.0
            except Exception:
                leverage = 0.0
            info = pos.get('info', {}) or {}
            symbol = info.get('symbol') or pos.get('symbol') or ''
            try:
                contracts = float(pos.get('contracts') or 0.0)
            except Exception:
                contracts = 0.0
            try:
                entry_price = float(pos.get('entryPrice') or 0.0)
            except Exception:
                entry_price = 0.0

            position = Position(symbol=symbol, side=side, amount=contracts,
                                entry_price=entry_price, exchange=EXCHANGE.BITGET, margin=leverage)

            # total_paid_funding = self.get_paid_funding(symbol, pos['timestamp'])
            if symbol.startswith("SXP"):
                continue
            raw_total_fee = info.get('totalFee')
            try:
                total_paid_funding = float(raw_total_fee) if raw_total_fee not in (None, '') else 0.0
            except Exception:
                total_paid_funding = 0.0
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