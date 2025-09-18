# src/client/testing_portfolio.py
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List
from collections import deque

from src.commons.multitf_feed import MultiTFFeedView
from src.commons.risk import StrategyRisk
from src.settings import backtest_config as cfg
from src.trading_strategies.abstract_strategy import Strategy
from src.utils import helpers
from src.utils.log import log, Label
from src.sizing_strategies.position_sizing import PositionSizer, FixedUnitsSizer, OrderContext

from src.commons import multitf_feed
from src.commons.date_containers import *


# --------- Helper: costs/slippage ----------
def _apply_slippage(price: float, points: int) -> float:
    # EURUSD 5-digit: 1 point = 0.00001
    return price + points * 1e-5

def _spread_half(points: int) -> float:
    return points * 1e-5 / 2.0

# --------- TestingPortfolio (one-call backtest) ----------
class TestingPortfolio:
    """
    Replays historical bars to a Strategy, simulates orders,
    and returns a summary dict from run().
    """

    def __init__(self, strategy: Strategy, initial_balance=cfg.INITIAL_BALANCE, symbol=cfg.SYMBOL,
                 sizer: PositionSizer | None = None, allow_window_adjust=False):
        self._tf = helpers.resolve_timeframe(getattr(cfg, "TIMEFRAME", "M1"))

        self.strategy = strategy
        self.initial_balance = float(initial_balance)
        self.symbol = symbol

        self.cash = float(initial_balance)
        self.positions: List[OpenPosition] = []  # open positions (can be many)
        self.trades: List[Trade] = []  # CLOSED trade records
        self.equity_curve: List[tuple[int, float]] = []
        self._next_pos_id: int = 1

        # leverage / margin (already in your file from earlier step)
        self.leverage: float = float(getattr(cfg, "LEVERAGE", 1.0))
        self.margin_used: float = 0.0
        self.peak_margin_used: float = 0.0

        # NEW: pluggable position sizer
        default_units = getattr(cfg, "ORDER_SIZE_UNITS", 10_000)
        self.sizer: PositionSizer = sizer or FixedUnitsSizer(default_units)

        # Feed view will be attached at run() time
        self.feed: MultiTFFeedView | None = None

        self.risk = getattr(strategy, "RISK", StrategyRisk())

        self._allow_window_adjust = allow_window_adjust

        self._resolved_symbol = None

    # ---- MAIN ENTRY (single method) ----
    def run(self, history: List[Bar]=None) -> dict:
        from src.utils import helpers  # ensure we use your initializer

        # 1) MT5 init via your helper
        helpers.initialize_mt5()
        bars = history if history is not None else multitf_feed.fetch_history_or_raise()

        try:
            # 2) Ensure symbol is visible/selected
            if not mt5.symbol_select(self.symbol, True):
                # show nearby matches to help with broker suffixes
                matches = [s.name for s in mt5.symbols_get(self.symbol + "*")] or []
                raise RuntimeError(
                    f"symbol_select('{self.symbol}') failed. "
                    f"Close matches in Market Watch: {matches[:10]}"
                )

            # 3) Fetch history (range first, then fallback)

            # 4) Warmup + attach feed view
            feed = MultiTFFeedView(bars=[], maxlen=max(cfg.WARMUP_BARS, 10))
            self.feed = feed  # NEW: store for sizers
            self.strategy.attach(feed)

            # 5) Replay bars to strategy
            for bar in bars:
                self.strategy.on_bar(bar)
                decision = self.strategy.decide()
                if decision == "BUY":
                    self._open(+1, bar)
                elif decision == "SELL":
                    self._open(-1, bar)
                elif decision == "CLOSE":
                    self._close(bar)
                self._mark(bar)

            # 6) Ensure flat & summarize
            if self.positions:
                self._close(bars[-1])

            summary = self._summarize()

            return summary

        finally:
            mt5.shutdown()

    # ---------- execution model ----------
    def _open(self, side: int, bar: Bar):
        # In netting mode, opening the opposite side flattens that side first
        if not self.risk.allow_hedging:
            self._close_side(bar, side=-side, size=None)

        px = self._entry_price(side, bar)

        same = self._positions_same_side(side)
        current_layer = len(same) + 1

        if not self.risk.allow_pyramiding:
            if same:
                log.log(Label.ORDER_REJECT, action="OPEN", side=side,
                        reason = "pyramiding is disabled; already in same-side position")
                return

        else:
            if current_layer > max(1, self.risk.max_layers):
                log.log(Label.ORDER_REJECT, action="OPEN", side=side,
                        reason = f"max layer reached ({current_layer} > {self.risk.max_layers}")
                return
            if self.risk.min_step_price:
                last_px = self._last_add_price(side)
                if last_px is not None:
                    moved = (px - last_px) if side == 1 else (last_px - px)
                    if moved < self.risk.min_step_price:
                        log.log(Label.ORDER_REJECT, action="OPEN", side=side,
                                reason = f"min step price not reached ({moved} < {self.risk.min_step_price})")
                        return

        equity_now = self._current_equity(bar)
        free_margin = equity_now - self.margin_used
        ctx = OrderContext(
            symbol=self.symbol,
            side=side,
            price=px,
            equity=equity_now,
            free_margin=free_margin,
            leverage=self.leverage,
            position=None,  # kept for backward-compat
            positions=tuple(self.positions),  # all open positions
            trades=tuple(self.trades),  # closed trades history
            feed=self.feed if self.feed is not None else MultiTFFeedView([], 1),
            bar=bar,
            layer=current_layer,
        )

        size = int(self.sizer.size(ctx))
        if size <= 0:
            log.log(Label.ORDER_REJECT, action="OPEN", side=side, reason="sizer returned 0")
            return

        # margin check
        req_margin = self._required_margin(size, px)
        if req_margin > free_margin:
            log.log(Label.ORDER_REJECT,
                    f"OPEN {('LONG' if side == 1 else 'SHORT')} {size}",
                    reason=f"Insufficient free margin (need {req_margin:.2f}, have {free_margin:.2f})")
            return

        # commission (half at entry)
        commission_in = cfg.COMMISSION_PER_LOT * (size / 100_000) / 2.0
        self.cash -= commission_in

        # book margin
        self.margin_used += req_margin
        self.peak_margin_used = max(self.peak_margin_used, self.margin_used)

        # create OPEN position
        pos = OpenPosition(
            id=self._next_pos_id,
            entry_time=bar.time,
            side=side,
            entry_px=px,
            size=size,
            commission_in=commission_in,
            layer = current_layer
        )
        self._next_pos_id += 1
        self.positions.append(pos)

        log.log(Label.ORDER_FILLED, action="OPEN", side=side, qty=size, price=px, pos_id=pos.id, layer=current_layer,
                bar_time=bar.time,)



    def _close(self, bar: Bar):
        self._close_side(bar, side=+1, size=None)
        self._close_side(bar, side=-1, size=None)

    def _close_side(self, bar: Bar, side: int, size: int | None):
        same_side = [p for p in self.positions if p.side == side]
        if not same_side:
            return
        fifo = getattr(cfg, "CLOSE_POLICY", "fifo").lower() == "fifo"
        order = sorted(same_side, key=lambda p: p.entry_time, reverse=not fifo)

        remaining = None if size is None else int(size)
        for p in order:
            if remaining == 0:
                break
            close_units = p.size if remaining is None else min(p.size, remaining)
            if close_units <= 0:
                continue

            px = self._exit_price(side, bar)
            pnl = side * (px - p.entry_px) * close_units
            commission_out = cfg.COMMISSION_PER_LOT * (close_units / 100_000) / 2.0
            self.cash += pnl - commission_out

            # release proportional margin
            req_margin_full = self._required_margin(p.size, p.entry_px)
            release = req_margin_full * (close_units / p.size)
            self.margin_used = max(0.0, self.margin_used - release)

            # closed trade record
            self.trades.append(Trade(
                entry_time=p.entry_time,
                exit_time=bar.time,
                side=side,
                entry_px=p.entry_px,
                exit_px=px,
                size=close_units,
                pnl=pnl,
                commission=p.commission_in * (close_units / p.size) + commission_out,
                layer=p.layer,
            ))

            p.size -= close_units
            if p.size <= 0:
                self.positions.remove(p)

            if remaining is not None:
                remaining -= close_units

            log.log(Label.ORDER_CLOSED, action="CLOSE", side=side, pnl=pnl, qty=close_units, price=px, pos_id=p.id,
                    layer=p.layer, bar_time=p.entry_time, close_time=bar.time)

    def _positions_same_side(self, side: int):
        return [p for p in self.positions if p.side == side and not p.closed]

    def _last_add_price(self, side: int):
        same = self._positions_same_side(side)
        return same[-1].entry_px if same else None

    def _entry_price(self, side: int, bar: Bar) -> float:
        if cfg.EXECUTION_MODE == "close":
            base = bar.close
        else:  # next_open (in backtest loop we only know current bar; assume next open ≈ current close)
            base = bar.close
        # apply spread (half to each side) + slippage in trade direction
        px = base + ( +_spread_half(cfg.SPREAD_POINTS) if side==1 else -_spread_half(cfg.SPREAD_POINTS) )
        px = px + ( +_apply_slippage(0, cfg.SLIPPAGE_POINTS) if side==1 else -_apply_slippage(0, cfg.SLIPPAGE_POINTS) )
        return px

    def _exit_price(self, side: int, bar: Bar) -> float:
        if cfg.EXECUTION_MODE == "close":
            base = bar.close
        else:
            base = bar.close
        px = base + ( -_spread_half(cfg.SPREAD_POINTS) if side==1 else +_spread_half(cfg.SPREAD_POINTS) )
        px = px - ( +_apply_slippage(0, cfg.SLIPPAGE_POINTS) if side==1 else -_apply_slippage(0, cfg.SLIPPAGE_POINTS) )
        return px

    def _mark(self, bar: Bar):
        equity = self.cash
        if self.position:
            px = bar.close
            mid = px  # simple
            pnl_unreal = self.position.side * (mid - self.position.entry_px) * self.position.size
            equity += pnl_unreal
        self.equity_curve.append((bar.time, equity))

    # ---------- summary ----------
    def _summarize(self) -> dict:
        eq = [e for _, e in self.equity_curve]
        ret = (eq[-1] - self.initial_balance) if eq else 0.0

        wins = [t for t in self.trades if t.pnl and t.pnl > 0]
        losses = [t for t in self.trades if t.pnl and t.pnl < 0]
        win_rate = (len(wins) / len(self.trades))*100 if self.trades else 0.0
        avg_win = sum(t.pnl for t in wins)/len(wins) if wins else 0.0
        avg_loss = sum(t.pnl for t in losses)/len(losses) if losses else 0.0
        profit_factor = (sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses))) if losses else math.inf

        # max drawdown
        peak, max_dd = -1e18, 0.0
        for x in eq:
            peak = max(peak, x)
            max_dd = max(max_dd, (peak - x))
        max_dd_pct = (max_dd/peak*100) if peak > 0 else 0.0

        # Sharpe (daily-ish for M1) — rough, no risk-free
        import numpy as np
        if len(eq) > 1:
            rets = np.diff(eq) / np.array(eq[:-1])
            sharpe = (np.mean(rets)/np.std(rets))*math.sqrt(252*24*60) if np.std(rets) > 0 else 0.0
        else:
            sharpe = 0.0
        summary = {
            "symbol": self.symbol,
            "from": datetime.fromtimestamp(self.equity_curve[0][0], tz=timezone.utc).isoformat() if self.equity_curve else None,
            "to":   datetime.fromtimestamp(self.equity_curve[-1][0], tz=timezone.utc).isoformat() if self.equity_curve else None,
            "start_balance": self.initial_balance,
            "end_balance": eq[-1] if eq else self.initial_balance,
            "net_profit": ret,
            "trades": len(self.trades),
            "win_rate_%": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if math.isfinite(profit_factor) else "inf",
            "max_drawdown_%": round(max_dd_pct, 2),
            "sharpe": round(sharpe, 2),
            "max_margin_used": round(self.peak_margin_used, 2),
            "max_margin_usage_%": round(
                (self.peak_margin_used / max([e for _, e in self.equity_curve] or [self.initial_balance])) * 100, 2
            ),
        }
        return summary

    def _current_equity(self, bar: Bar) -> float:
        equity = self.cash
        mid = bar.close
        for p in self.positions:
            equity += p.side * (mid - p.entry_px) * p.size
        return equity

    def _mark(self, bar: Bar):
        self.equity_curve.append((bar.time, self._current_equity(bar)))

    def _required_margin(self, units: int, price: float) -> float:
        """
        Approximate required margin in account currency (USD assumed, but will
        try to convert via live ticks). Works well for majors.
        """
        import MetaTrader5 as mt5
        acc = getattr(mt5.account_info(), "currency", "USD") or "USD"
        base, quote = self._symbol_parts(self.symbol)

        # Value notional in account currency
        if acc == "USD":
            if quote == "USD":
                notional_usd = units * price  # e.g., EURUSD
            elif base == "USD":
                notional_usd = units  # e.g., USDJPY
            else:
                # cross (e.g., EURGBP): convert quote->USD
                notional_quote = units * price  # in quote ccy
                notional_usd = self._convert_to_usd(quote, notional_quote)
        else:
            # non-USD account: best-effort via USD bridge
            if quote == acc:
                notional_usd = units * price
                notional_usd = self._convert_between_ccy(quote, "USD", notional_usd)
            elif base == acc:
                notional_usd = units
                notional_usd = self._convert_between_ccy(base, "USD", notional_usd)
            else:
                # cross both ways: base->USD via quote, etc. Best-effort.
                notional_quote = units * price
                notional_usd = self._convert_to_usd(quote, notional_quote)

        margin = notional_usd / max(self.leverage, 1.0)
        return float(margin)

    def _symbol_parts(self, symbol: str) -> tuple[str, str]:
        s = symbol.upper()
        if len(s) >= 6:
            return s[:3], s[-3:]
        return s, ""

    def _convert_to_usd(self, ccy: str, amount: float) -> float:
        """Convert amount in 'ccy' to USD using live ticks where possible."""
        if ccy.upper() == "USD":
            return amount
        import MetaTrader5 as mt5
        pair = f"{ccy.upper()}USD"
        tick = mt5.symbol_info_tick(pair)
        if tick and tick.bid:
            return amount * float(tick.bid)
        inv = f"USD{ccy.upper()}"
        tick = mt5.symbol_info_tick(inv)
        if tick and tick.ask:
            return amount / float(tick.ask)
        return amount  # fallback

    def _convert_between_ccy(self, src: str, dst: str, amount: float) -> float:
        """Convert between arbitrary currencies via available USD legs."""
        if src.upper() == dst.upper():
            return amount
        if dst.upper() == "USD":
            return self._convert_to_usd(src, amount)
        # src->USD->dst
        usd = self._convert_to_usd(src, amount)
        # USD->dst
        if dst.upper() == "USD":
            return usd
        import MetaTrader5 as mt5
        pair = f"USD{dst.upper()}"
        tick = mt5.symbol_info_tick(pair)
        if tick and tick.ask:
            return usd * float(tick.ask)  # USD priced in dst
        inv = f"{dst.upper()}USD"
        tick = mt5.symbol_info_tick(inv)
        if tick and tick.bid:
            return usd / float(tick.bid)
        return usd  # fallback

    @staticmethod
    def _fmt_xticks(ax, times):
        if not times: return
        import matplotlib.dates as mdates
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))


from datetime import timezone, datetime
import MetaTrader5 as mt5

def _utc_naive(dt: datetime) -> datetime:
    """
    MT5 expects UTC-naive datetimes for history functions.
    We accept both aware and naive and convert to naive UTC.
    """
    if dt.tzinfo is None:
        # assume already UTC-naive
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def _bars_from_rates(rates) -> list[Bar]:
    return [
        Bar(
            time=int(r["time"]),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            tick_volume=int(r["tick_volume"]),
        )
        for r in rates
    ]

def _friendly_last_error() -> str:
    try:
        code, detail = mt5.last_error()
        return f"{code} {detail}"
    except Exception:
        return "unknown"

def _approx_bar_count(start: datetime, end: datetime, tf: int) -> int:
    secs = (end - start).total_seconds()
    return max(10, int(secs // helpers.tf_seconds(tf)))
