from dataclasses import dataclass

import MetaTrader5 as mt5

from src.client.testing_portfolio import Bar
from src.commons.multitf_feed import MultiTFFeedView
from src.commons.risk import StrategyRisk
from src.indicators.moving_average import SimpleMovingAverage, ExponentialMovingAverage
from src.optimizer.space import IntParam, CategoricalParam, FloatParam
from src.trading_strategies.abstract_strategy import Strategy
from src.settings import backtest_config as cfg

READABLE_FORMAT = "Moving Average Crossover Scalping"

# What to Optimize
OPT_SPACE = [
    IntParam("fast", 5, 40, 1),
    IntParam("slow", 20, 200, 5),
    IntParam("general", 50, 300, 10),
    CategoricalParam("ma_type", ["SMA", "EMA"])
]

# What stays fixed
FIXED_PARAMS = {
    "current_state": 1,
}

# Default values for parameters
DEFAULT_PARAMS = {
    "fast": 20,
    "slow": 50,
    "general": 100,
    "ma_type": "SMA",
    "current_state": 1,
}

def _rule_fast_lt_slow(p: dict) -> bool:
    return int(p['fast']) < int(p['slow']) < int(p['general'])

RULES = [_rule_fast_lt_slow]

@dataclass
class MACrossoverScalping(Strategy):
    fast: int = 20
    slow: int = 50
    general: int = 100

    ma_type: str = "SMA"
    current_state: int = 1 # +1 means uptrend (bullish), 0 means sideways, -1 means downtrend (bearish)

    RISK = StrategyRisk(
        allow_hedging=False,
        allow_pyramiding=False,
    )
    def on_bar(self, bar: Bar):
        """
        When a new bar is introduced, update the moving averages, ensuring that it is a moving average
        :param bar:
        :return: Nothing, update the moving average trackers for both the slow and the fast and also the window
        """
        self.feed.push(bar)

        self.ma_fast.push(bar.close)
        self.ma_slow.push(bar.close)
        self.ma_general.push(bar.close)


    def decide(self):
        f = self.ma_fast.get()
        s = self.ma_slow.get()
        g = self.ma_general.get()

        if f > s > g:
            return "BUY"
        elif f < s < g:
            return "SELL"
        else:
            return None

    def __post_init__(self):
        if self.ma_type == "SMA":
            self.ma_fast = SimpleMovingAverage(k=self.fast)
            self.ma_slow = SimpleMovingAverage(k=self.slow)
            self.ma_general = SimpleMovingAverage(k=self.general)
        elif self.ma_type == "EMA":
            self.ma_fast = ExponentialMovingAverage(k=self.fast)
            self.ma_slow = ExponentialMovingAverage(k=self.slow)
            self.ma_general = ExponentialMovingAverage(k=self.general)
        else:
            raise ValueError("the ma_type is not recognized")

    def _post_feed_init(self):
        # Setup the slow and fast MA
        closes_fast = self.feed.get_last_n_closes(self.fast)
        closes_slow = self.feed.get_last_n_closes(self.slow)
        closes_general = self.feed.get_last_n_closes(self.general)

        for c in closes_fast:
            self.ma_fast.push(c)

        for c in closes_slow:
            self.ma_slow.push(c)

        for c in closes_general:
            self.ma_general.push(c)


def initialize_strategy(**params) -> Strategy:
    p = {**DEFAULT_PARAMS, **FIXED_PARAMS, **params}

    if not _rule_fast_lt_slow(p):
        raise ValueError(f"Invalid params: fast({p['fast']}) must be < slow({p['slow']})")

    return MACrossoverScalping(
        fast = int(p["fast"]),
        slow = int(p["slow"]),
        ma_type = p["ma_type"],
        current_state = int(p["current_state"]),
    )