# -------- Data containers --------
from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    time: int      # unix seconds
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int

@dataclass
class OpenPosition:
    id: int
    entry_time: int
    side: int             # +1 long, -1 short
    entry_px: float
    size: int             # remaining open units
    commission_in: float  # commission taken at entry (half round-trip)
    layer: int = 1
    closed: bool = False

@dataclass
class Trade:              # closed deal record
    entry_time: int
    exit_time: int
    side: int
    entry_px: float
    exit_px: float
    size: int
    pnl: float
    commission: float     # full round-trip commission for this closed size
    layer: int = 1