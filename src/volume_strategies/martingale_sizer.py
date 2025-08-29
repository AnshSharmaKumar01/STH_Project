from .position_sizing import PositionSizer, OrderContext

READABLE_FORMAT = "Martingale Sizer (Double Every Loss)"

class MartingaleSizer(PositionSizer):
    def __init__(self, base_units: int, streak_cap):
        self.base = int(base_units)
        self.streak_cap = streak_cap

    def size(self, ctx: OrderContext) -> int:
        streak = 0
        for t in reversed(ctx.trades):
            if t.pnl is None:
                break
            if t.pnl < 0:
                streak += 1
            else:
                break
        if streak > self.streak_cap:
            streak = self.streak_cap - streak

        return int(self.base * (2 ** streak))