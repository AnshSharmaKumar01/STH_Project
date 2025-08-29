from src.client.portfolio import AbstractPortfolio
from src.settings import config
from src.trading_strategies.abstract_strategy import Strategy
from src.utils import helpers
import MetaTrader5 as mt5


class TradingPortfolio(AbstractPortfolio):
    """
    This portfolio is used for actual trading, used once the bot is fully tested and ready to be deployed
    """
    def __init__(self, strategy: Strategy, initial_balance=None, symbol=config.SYMBOL):
        helpers.initialize_mt5()
        self.strategy = strategy

        if initial_balance is None:
            account_info = mt5.account_info()._asdict()
            initial_balance = account_info.get("balance")

        super().__init__(initial_balance, symbol)

    def run(self):
        # TODO - Imeplement the portfolio trading starting
        pass