
class AccountBalance:
    def __init__(self, total_margin_balance, total_initial_margin, total_maint_margin, available_balance, unrealized_pnl):
        self.total_margin_balance = total_margin_balance
        self.total_initial_margin = total_initial_margin
        self.total_maint_margin = total_maint_margin
        self.margin_level = self.total_margin_balance / self.total_initial_margin if self.total_initial_margin > 0 else 0
        self.maint_margin_coverage = self.total_margin_balance / self.total_maint_margin if self.total_maint_margin > 0 else 0
        self.available_balance = available_balance
        self.unrealized_pnl = unrealized_pnl

    def __repr__(self):
        return (f"AccountBalance(total_margin_balance={self.total_margin_balance}, "
                f"total_initial_margin={self.total_initial_margin}, "
                f"total_maint_margin={self.total_maint_margin}, "
                f"margin_level={self.margin_level}, "
                f"maint_margin_coverage={self.maint_margin_coverage}, "
                f"available_balance={self.available_balance}, "
                f"unrealized_pnl={self.unrealized_pnl})")


class Tracker:
    def __init__(self):
        """
        Initialize the Tracker with a ccxt Binance client.
        """
        self.client = None  # This should be set in subclasses

    def get_open_positions(self):
        """
        Get all currently open positions on Binance Futures.

        Returns:
            List of open positions (Position objects)
        """
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_cross_margin_account_info(self):
        """
        Fetch cross margin account information and calculate ROI for each asset.

        Returns:
            AccountBalance object with account details
        """
        raise NotImplementedError("This method should be implemented in subclasses")