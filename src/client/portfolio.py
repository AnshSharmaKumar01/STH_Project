import MetaTrader5 as mt5
import pandas as pd

from src.commons.summaries import SummaryType
from src.commons.trade import Trade
from src.settings import config, backtest_config
from src.utils import helpers
from abc import ABC, abstractmethod

from datetime import datetime, timezone

from src.trading_strategies.abstract_strategy import Strategy


class AbstractPortfolio(ABC):
    def __init__(self, initial_balance, symbol=config.SYMBOL):
        self.initial_balance: float = initial_balance
        self.current_balance: float = initial_balance

        self.symbol: str = symbol


    @abstractmethod
    def run(self):
        pass

    def update_balance(self, profit):
        """
        Adds the profit made from a trade to the current balance
        :param profit: The profit of a trade (if loss then represent as negative)
        :return: updates the current balance of the portfolio
        """
        self.current_balance += profit

    def get_symbol(self):
        return self.symbol