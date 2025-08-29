# src/trading_strategies/abstract_strategy.py
from abc import ABC, abstractmethod
from typing import Protocol, List

from src.commons.date_containers import Bar
from src.commons.multitf_feed import MultiTFFeedView
from src.commons.risk import StrategyRisk

class Strategy(ABC):
    RISK: StrategyRisk = StrategyRisk()
    """
    Implement these minimal hooks. Keep it simple so writing trading_strategies is fast.
    """
    def attach(self, feed: MultiTFFeedView) -> None:
        """Called once before the run; store feed if you need rolling data."""
        self.feed = feed
        self._post_feed_init()

    def _post_feed_init(self):
        """Called after the feed is initialized, used to initialize anything that needs the feed (like MA)"""
        pass

    def on_bar(self, bar: Bar) -> None:
        """Called for each completed bar (backtest uses historic bars)."""
        self.feed.push(bar)

    @abstractmethod
    def decide(self) -> str | None:
        """
        Return one of: 'BUY', 'SELL', 'CLOSE', or None.
        Called right after on_bar() so you decide with fresh state.
        """