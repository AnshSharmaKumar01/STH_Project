# src/strategies/ma_crossover/tester_strategy.py
from __future__ import annotations
from dataclasses import dataclass

from src.commons.risk import StrategyRisk
from src.trading_strategies.abstract_strategy import Strategy
from src.optimizer.space import IntParam

READABLE_FORMAT = "Test Strategy"
# what can be tuned:
OPT_SPACE = [
    IntParam("fast", 5, 40, 1),
    IntParam("slow", 20, 200, 5),
]
# what must remain fixed during optimization:
FIXED_PARAMS = {
    "ma_type": "SMA",         # or EMA, etc.
}
DEFAULT_PARAMS = {
    "fast": 10,
    "slow": 30,
    "state": 0,
}
# rules the optimizer must respect:
def _rule_fast_lt_slow(p: dict) -> bool:
    return int(p["fast"]) < int(p["slow"])

RULES = [_rule_fast_lt_slow]

# --- strategy implementation ---
@dataclass
class TestStrategy(Strategy):
    fast: int = 10
    slow: int = 30
    ma_type: str = "SMA"
    state: int = 0

    RISK = StrategyRisk(
        allow_hedging=False,
        allow_pyramiding=True,
        max_layers=5
    )

    def decide(self):
        closes = self.feed.get_last_n_closes(max(self.fast, self.slow))
        if len(closes) < max(self.fast, self.slow):
            return None
        f = sum(closes[-self.fast:]) / self.fast
        s = sum(closes[-self.slow:]) / self.slow
        if self.state <= 0 and f > s:
            self.state = 1
            return "BUY"
        if self.state >= 1 and f < s:
            self.state = -1
            return "SELL"
        return None

# --- factory: make it robust to missing args ---
def initialize_strategy(**params) -> Strategy:
    # order matters: DEFAULTS < FIXED < user/optimizer overrides
    p = {**DEFAULT_PARAMS, **FIXED_PARAMS, **params}
    # enforce rule here too (nice early safeguard)
    if not _rule_fast_lt_slow(p):
        raise ValueError(f"Invalid params: fast({p['fast']}) must be < slow({p['slow']})")
    return TestStrategy(
        fast=int(p["fast"]),
        slow=int(p["slow"]),
        ma_type=p["ma_type"],
        state=p["state"],
    )
