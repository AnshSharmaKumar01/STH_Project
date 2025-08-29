# src/engine/position_sizing.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, Tuple

# forward decls to avoid circular imports
class MultiTFFeedView(Protocol):
    def get_last_n_bars(self, n: int): ...
    def get_last_n_closes(self, n: int): ...

@dataclass(frozen=True)
class OrderContext:
    symbol: str
    side: int                     # +1 long, -1 short (for the order being considered)
    price: float
    equity: float
    free_margin: float
    leverage: float
    position: Optional[object]    # DEPRECATED: None when multi-pos; kept for old sizers
    positions: Tuple[object, ...] # NEW: all open positions (immutable snapshot)
    trades: Tuple[object, ...]    # closed trades history
    feed: MultiTFFeedView
    bar: object
    layer: int = 1


class PositionSizer(Protocol):
    def size(self, ctx: OrderContext) -> int:
        """Return desired position SIZE in UNITS (e.g., 10_000 = 0.10 lot)."""

class FixedUnitsSizer:
    """Placeholder: always return a fixed number of units from config."""
    def __init__(self, units: int):
        self.units = int(units)

    def size(self, ctx: OrderContext) -> int:
        return self.units
