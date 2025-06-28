import ccxt

import Config
import Exchange.Exchange
from Core.Define import PositionSide, Position, EXCHANGE
from Tracker.Tracker import AccountBalance
from Tracker import Tracker

class BinanceTracker:


    def __init__(self):
        """
        Initialize the Tracker with a ccxt Binance client.

        Args:
            api_key: Your Binance API key.
            api_secret: Your Binance API secret.
        """
        self.client = Exchange.Exchange.binance_exchange

    def get_open_positions(self):
        """
        Get all currently open positions on Binance Futures.

        Args:
            client: An instance of binance.client.Client

        Returns:
            List of open positions (dicts)
        """
        positions = []
        response = self.client.fetch_positions()
        positions_json = [pos for pos in response if pos['info']['positionAmt'] != '0']
        for pos in positions_json:
            symbol = pos['info']['symbol']
            side = PositionSide.LONG if pos['side'].upper() == 'LONG' else PositionSide.SHORT
            leverage = 1 / float(pos['initialMarginPercentage'])
            position = Position(symbol=symbol, side=side, amount=float(pos['info']['positionAmt']),
                                entry_price=float(pos['entryPrice']), exchange=EXCHANGE.BINANCE, margin=leverage)

            total_paid_funding = self.get_paid_funding(symbol, pos['timestamp'])
            position.set_paid_funding(total_paid_funding)

            positions.append(position)
        # amount = float(positions[0]['info']['positionAmt'])
        # side = positions[0]['side']
        margin_account = self.client.sapi_get_margin_account()
        for user_asset in margin_account.get('userAssets', []):
            borrowed = float(user_asset.get('borrowed', 0))
            free = float(user_asset.get('free', 0))
            if borrowed > 0 or free > 0:
                symbol = user_asset['asset']
                # borrowed an sell -> Short position
                position = Position(symbol=symbol + "USDT", side=PositionSide.SHORT, amount=free, entry_price=0, exchange=EXCHANGE.BINANCE, margin=1.0)
                positions.append(position)

        return positions

    def get_cross_margin_account_info(self):
        """
        Fetch cross margin account information and calculate ROI for each asset.

        Returns:
            List of dicts with asset, total balance, borrowed, net asset, and ROI.
        """
        account_info = self.client.fetchBalance()
        info = account_info['info']
        total_margin_balance = float(info['totalMarginBalance'])
        total_initial_margin = float(info['totalInitialMargin'])
        total_maint_margin = float(info['totalMaintMargin'])
        available_balance = float(info['availableBalance'])
        unrealized_pnl = float(info['totalUnrealizedProfit'])


        account_balance = AccountBalance(total_margin_balance,
                                         total_initial_margin,
                                         total_maint_margin,
                                         available_balance,
                                         unrealized_pnl)
        return account_balance

    def get_current_funding_rate(self, symbol):
        """
        Get the current funding rate for a given symbol.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').

        Returns:
            The current funding rate as a float.
        """
        try:
            funding_rate = self.client.fetchFundingRate(symbol)
            funding_rate = float(funding_rate['fundingRate']) * 100
            funding_rate = round(funding_rate, 4)
            return funding_rate
        except:
            return 0.0


    def get_current_funding_rate_list(self, symbols):
        """
        Get the current funding rates for a list of symbols.

        Args:
            symbols: List of trading pair symbols (e.g., ['BTC/USDT', 'ETH/USDT']).

        Returns:
            A dictionary with symbols as keys and their funding rates as values.
        """
        funding_rates = {}
        for symbol in symbols:
            funding_rate = self.get_current_funding_rate(symbol)
            funding_rates[symbol] = funding_rate
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
            funding_history = self.client.fetchFundingHistory(symbol=symbol, since=start_time,  limit=500)
            total_paid = sum(float(funding['amount']) for funding in funding_history)
            return total_paid
        except Exception as e:
            print(f"Error fetching funding history for {symbol}: {e}")
            return 0.0

    def get_paid_fees(self, symbol, start_time):
        """
        Get the total fees paid for a given symbol.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').

        Returns:
            The total fees paid as a float.
        """
        try:
            trades = self.client.fetchMyTrades(symbol=symbol, since=start_time, limit=500)
            total_fees = sum(float(trade['fee']['cost']) for trade in trades)
            return total_fees
        except Exception as e:
            print(f"Error fetching trade history for {symbol}: {e}")
            return 0.0