# src/volume_strategies/win_streak_sizer.py
from .position_sizing import PositionSizer, OrderContext

READABLE_FORMAT = "Win Streak Sizer (+20% per win, cap 3)"

class WinStreakSizer(PositionSizer):
    def __init__(self, base_units: int):
        self.base = int(base_units)

    def size(self, ctx: OrderContext) -> int:
        # count consecutive wins at the end of history
        streak = 0
        for t in reversed(ctx.trades):
            if t.pnl is None: break
            if t.pnl > 0: streak += 1
            else: break
        if streak > 3: streak = 3
        return int(self.base * (1.2 ** streak))

def initialize_sizer() -> PositionSizer:
    from src.settings import backtest_config as cfg
    return WinStreakSizer(getattr(cfg, "ORDER_SIZE_UNITS", 10_000))
