from dataclasses import dataclass

from src.client.testing_portfolio import Bar
from src.commons.risk import StrategyRisk
from src.indicators.moving_average import SimpleMovingAverage
from src.optimizer.space import IntParam, CategoricalParam, FloatParam
from src.trading_strategies.abstract_strategy import Strategy

READABLE_FORMAT = "Trading Strategy Template"

# What to Optimize
OPT_SPACE = [
    IntParam("a", 5, 40, 1),
    FloatParam("b", 1.0, 2.0, 0.1),
    CategoricalParam("c", ["1", "2"])
]

# What stays fixed
FIXED_PARAMS = {
    "d": 1,
}

# Default values for parameters
DEFAULT_PARAMS = {
    "a": 20,
    "b": 1.5,
    "c": "1",
    "d": 1,
}

def _rule_template(p: dict) -> bool:
    return int(p['a']) < float(p['b'])

RULES = [_rule_template]

@dataclass
class TradingStrategyTemplate(Strategy):
    a: int = 20
    b: float = 1.5
    c: str = "1"
    d: int = 1

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
        pass


    def decide(self):
        """
        This is called after on_bar. This method returns the decision for buy/sell/nothing. Before this method is
        called, everything should be updated during on_bar, so just the decision logic needs to be here

        :return: "Buy" or "Sell" or None
        """

        return None

    def __post_init__(self):
        """
        After the strategy is initialized, if needed, additional variables can be introduced. This is where the
        indicators should be initialized.
        """
        self.e = SimpleMovingAverage(k=10)

    def _post_feed_init(self):
        """
        This is called once the feed is initialized. Here you can initialize indicators that need past values,
        like a moving average.
        """
        # Setup the slow and fast MA
        closes_e = self.feed.get_last_n_closes(10)

        for c in closes_e:
            self.e.push(c)

def initialize_strategy(**params) -> Strategy:
    p = {**DEFAULT_PARAMS, **FIXED_PARAMS, **params}

    if not _rule_template(p):
        raise ValueError(f"Invalid params: fast({p['fast']}) must be < slow({p['slow']})")

    return TradingStrategyTemplate(
        a = p['a'],
        b = p['b'],
        c = p['c'],
        d = p['d'],
    )