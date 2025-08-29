from collections import deque
from typing import List, Protocol

from src.commons.date_containers import Bar
from src.utils import helpers
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
import pandas as pd
from src.settings import backtest_config as cfg

def resolve_symbol(symbol=cfg.SYMBOL):
    from src.utils import helpers
    import MetaTrader5 as mt5

    helpers.initialize_mt5()  # idempotent

    # Try exact → wildcard
    exact = mt5.symbol_info(symbol)
    if exact:
        resolved = exact.name
    else:
        syms = mt5.symbols_get(f"{symbol}*") or []
        names = [s.name for s in syms]
        if not names:
            term = mt5.terminal_info()
            raise RuntimeError(
                f"Unable to resolve symbol '{symbol}'. "
                f"connected={getattr(term, 'connected', False)} last_error={mt5.last_error()}"
            )
        # prefer exact string match if present else first candidate
        resolved = symbol if symbol in names else names[0]

    # **Select** it so history functions are allowed to use it
    if not mt5.symbol_select(resolved, True):
        raise RuntimeError(f"symbol_select({resolved}) failed: {mt5.last_error()}")

    return resolved

def fetch_history_or_raise(tf=cfg.TIMEFRAME):

    helpers.initialize_mt5()

    symbol = resolve_symbol(cfg.SYMBOL)


    # --- probe small recent slice
    probe = mt5.copy_rates_from_pos(symbol, tf, 0, 2000)
    if _mt5_empty(probe):
        now = datetime.now(timezone.utc)
        last_30 = mt5.copy_rates_range(symbol, tf, now - timedelta(days=30), now)
        if _mt5_empty(last_30):
            err = mt5.last_error()
            term = mt5.terminal_info()
            raise RuntimeError(
                f"No data available at all for {symbol} tf={tf}. "
                f"connected={getattr(term, 'connected', False)} last_error={err}. "
                "Open the symbol’s chart once or download history in MT5 (Tools → History Center)."
            )
        probe = last_30

    pf = pd.DataFrame(probe)
    pf["time"] = pd.to_datetime(pf["time"], unit="s", utc=True)

    avail_start_utc = pf["time"].min().to_pydatetime()
    avail_end_utc = pf["time"].max().to_pydatetime()

    # requested window (ensure tz-aware)
    req_start = cfg.DATE_START
    req_end = cfg.DATE_END
    if req_start.tzinfo is None: req_start = req_start.replace(tzinfo=timezone.utc)
    if req_end.tzinfo is None: req_end = req_end.replace(tzinfo=timezone.utc)

    # ask for the requested window directly
    bars = mt5.copy_rates_range(symbol, tf, req_start, req_end)

    # optional clamp if empty
    if _mt5_empty(bars) and getattr(cfg, "AUTO_ADJUST_HISTORY_WINDOW", True):
        start = max(req_start, avail_start_utc)
        end = min(req_end, avail_end_utc)
        if start < end:
            bars = mt5.copy_rates_range(symbol, tf, start, end)

    if _mt5_empty(bars):
        err = mt5.last_error()
        raise RuntimeError(
            "Requested window has no overlap with server history or the server returned nothing.\n"
            f"Requested: [{req_start.isoformat()} .. {req_end.isoformat()}]\n"
            f"Probe shows at least: [{avail_start_utc.isoformat()} .. {avail_end_utc.isoformat()}] (UTC)\n"
            f"Symbol={symbol} tf={tf} last_error={err}"
        )

    result = []
    for i, b in enumerate(bars):
        result.append(Bar(
            b[0],
            b[1],
            b[2],
            b[3],
            b[4],
            b[5],
            b[6],
            b[7]
        ))
    return result

def _mt5_empty(arr) -> bool:
    # Works for None, list/tuple, numpy arrays, pandas Series/DataFrames
    if arr is None:
        return True
    try:
        return len(arr) == 0  # fast path for sequences
    except Exception:
        pass
    # numpy objects often have .size
    size = getattr(arr, "size", None)
    return size == 0

class MultiTFFeedView:
    def __init__(self, bars: List[Bar], maxlen: int, tf=cfg.TIMEFRAME):
        self._tf = tf
        self._bars = bars
        self._window = deque(maxlen=maxlen)
        self._storage = []
        self._storage_capacity = helpers.tf_minutes(tf)

    def push(self, bar: Bar):
        """
        Add a new bar to the feedview. This version, takes the timeframe into consideration. If the timeframe is higher,
        then the bars are stored in the _storage, and once enough bars are ready, the new timeframe bar value will be
        added to the _window
        :param bar:
        :return:
        """
        self._storage.append(bar)
        if len(self._storage) == self._storage_capacity:
            self._extract_bar_from_m1()

    def get_last_n_bars(self, n: int) -> List[Bar]:
        n = min(n, len(self._window))
        return list(self._window)[-n:]

    def get_last_n_closes(self, n: int) -> List[float]:
        return [b.close for b in self.get_last_n_bars(n)]

    def _extract_bar_from_m1(self):
        if len(self._storage) != self._storage_capacity:
            raise ValueError("Storage is not full yet!")

        time = self._storage[0].time
        open = self._storage[0].open
        high = max([b.high for b in self._storage])
        low =  min([b.low for b in self._storage])
        close = self._storage[-1].close
        tick_volume = sum(b.tick_volume for b in self._storage)
        spread = self._storage[-1].spread
        real_volume = sum(b.real_volume for b in self._storage)

        new_bar = Bar(time, open, high, low, close, tick_volume, spread, real_volume)
        self._window.append(new_bar)

        self._storage = []