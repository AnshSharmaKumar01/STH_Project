# simple typed params + grid generator + rule checking
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence, Callable, Dict, Any, List
import itertools

Rule = Callable[[Dict[str, Any]], bool]   # returns True if valid

@dataclass(frozen=True)
class IntParam:
    name: str
    low: int
    high: int
    step: int = 1
    def values(self) -> Iterable[int]:
        return range(self.low, self.high + 1, self.step)

@dataclass(frozen=True)
class FloatParam:
    name: str
    low: float
    high: float
    step: float
    def values(self) -> Iterable[float]:
        # safe step iteration
        v = self.low
        while v <= self.high + 1e-12:
            yield round(v, 10)
            v += self.step

@dataclass(frozen=True)
class CategoricalParam:
    name: str
    choices: Sequence[Any]
    def values(self) -> Iterable[Any]:
        return list(self.choices)

def grid(params: Sequence[Any]) -> Iterable[Dict[str, Any]]:
    if not params:
        yield {}
        return
    names = [p.name for p in params]
    value_lists = [list(p.values()) for p in params]
    for combo in itertools.product(*value_lists):
        yield dict(zip(names, combo))

def grid_size(params: Sequence[Any], rules: Iterable[Rule] | None = None) -> int:
    if not params:
        return 1
    names = [p.name for p in params]
    value_lists = [list(p.values()) for p in params]

    pred = combine_rules(rules)
    if pred is None:
        return math.prod(len(v) for v in value_lists)  # fast path

    count = 0
    for combo in itertools.product(*value_lists):
        cand = dict(zip(names, combo))
        if pred(cand):
            count += 1
    return count

def combine_rules(rules: Iterable[Rule] | None) -> Rule | None:
    if not rules:
        return None
    def _all_ok(params: Dict[str, Any]) -> bool:
        for r in rules:
            if not r(params):
                return False
        return True
    return _all_ok

def obeys(rules: Sequence[Rule], p: Dict[str, Any]) -> bool:
    return all(rule(p) for rule in rules)
