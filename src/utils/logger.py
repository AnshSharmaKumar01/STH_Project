# src/utils/logger.py
from __future__ import annotations

import json
import time
import threading
from enum import Enum, auto
from queue import Queue, Full, Empty
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional
import os
from pathlib import Path
from datetime import datetime, timezone

from matplotlib.pyplot import bar_label

from src.trading_strategies.abstract_strategy import Strategy
from src.utils.formatting import format_summary


# --- 1) Declare your labels here ---------------------------------------------

class Label(Enum):
    ORDER_FILLED        = auto()
    ORDER_REJECT        = auto()
    HEARTBEAT           = auto()
    EXECUTION_ERR       = auto()
    PNL_SNAPSHOT        = auto()
    ORDER_CLOSED        = auto()
    SUMMARY             = auto()
    LOGGER_ERROR        = auto()
    OPTIMIZATION_RESULT = auto()
    SETUP_COMPLETE      = auto()
    # 👉 Add new labels above; then add a formatter in _FORMATTERS below.


# --- 2) For each label, define how the inputs -> string -----------------------

# A formatter is any Callable that takes *inputs, **kwargs and returns a str.
Formatter = Callable[..., str]

# --- flexible formatters -----------------------------------------------

def _side_to_text(side):
    if isinstance(side, int):
        return "LONG" if side > 0 else "SHORT"
    return str(side).upper() if side else ""

def _fmt_order_filled(*args, **kw) -> str:
    """
    Flexible:
      - If you pass a single string -> use it as-is.
      - Or pass kwargs: action=("OPEN"/"CLOSE"), side=(+1/-1/"LONG"/"SHORT"),
        qty/int/size, price/px, pos_id (optional).
    """
    # plain text passthrough
    if args and len(args) == 1 and isinstance(args[0], str) and not kw:
        return args[0]

    action = kw.get("action", "ORDER")
    side = _side_to_text(kw.get("side"))
    qty = kw.get("qty", kw.get("size"))
    price = kw.get("price", kw.get("px"))
    pos_id = kw.get("pos_id")
    bar_time = kw.get("bar_time")
    layer = kw.get("layer")

    if side and qty is not None and price is not None:
        core = f"{action} {side} {int(qty)} @ {float(price):.5f}"
        if layer is not None:
            core += f" (layer = {layer})"

        if pos_id is not None:
            core += f" (pos#{pos_id})"

        if bar_time is not None:
            core += f" (bar_time = {datetime.fromtimestamp(bar_time, tz=timezone.utc)})"


        return core


    # last-resort fallback so we never crash
    leftovers = " ".join(str(a) for a in args)
    return f"{action} {side} {qty or ''} @ {price or ''} {leftovers} {kw}".strip()

def _fmt_order_reject(*args, **kw) -> str:
    """
    Same flexibility as filled; include an optional reason.
    """
    if args and len(args) == 1 and isinstance(args[0], str) and not kw:
        return args[0]

    action = kw.get("action", "CLOSE")
    reason = kw.get("reason", "")
    side = _side_to_text(kw.get("side"))
    qty = kw.get("qty", kw.get("size"))
    price = kw.get("price", kw.get("px"))

    head = f"REJECT {action}"
    if side or qty or price is not None:
        head += f" {side} {qty or ''} @ {price or ''}".rstrip()
    if reason:
        head += f" — {reason}"
    return head

def _fmt_order_closed(*args, **kw):

    # If the log is plaintext, instead of parameters
    if args and len(args) == 1 and isinstance(args[0], str) and not kw:
        return args[0]

    action = kw.get("action", "ORDER")
    side = _side_to_text(kw.get("side"))
    qty = kw.get("qty", kw.get("size"))
    price = kw.get("price", kw.get("px"))
    pnl= kw.get("pnl")
    pos_id = kw.get("pos_id")
    bar_time = kw.get("bar_time")
    layer = kw.get("layer")
    close_time = kw.get("close_time")


    if side and qty is not None and price is not None:
        core = f"{action} {side} {int(qty)} @ {float(price):.5f} {float(price):.5f}"

        if layer is not None:
            core += f" (layer = {layer})"

        if pos_id is not None:
            core += f" (pos#{pos_id})"

        if bar_time is not None:
            core += f" (bar_time = {datetime.fromtimestamp(bar_time, tz=timezone.utc)})"

        if close_time is not None:
            core += f" (close_time = {datetime.fromtimestamp(close_time, tz=timezone.utc)}"
        return core


    # last-resort fallback so we never crash
    leftovers = " ".join(str(a) for a in args)
    return f"{action} {side} {qty or ''} @ {price or ''} {leftovers} {kw}".strip()


def _fmt_heartbeat(ok: bool):
    return "ok=1" if ok else "ok=0"

def _fmt_execution_err(what, exc):
    return f"{what}: {type(exc).__name__}({exc})"

def _fmt_pnl_snapshot(equity, m2m, exposure):
    return f"equity={equity:.2f} m2m={m2m:.2f} exposure={exposure:.2f}"

def _fmt_summary(summary):
    return summary

def _fmt_logger_error(error):
    return error

def _fmt_optimization_result(*args, **kw):
    eval_num = kw.get("eval_num")
    score = kw.get("score")
    params = kw.get("params")
    summary = kw.get("summary")

    return f"optimization number {eval_num} - final score : {score} - params : {params} - summary : {format_summary(summary)}"

def _fmt_setup_complete(*args, **kw):
    run_type = kw.get("run_type")
    trade_strategy = kw.get("trade_strategy")
    volume_strategy = kw.get("volume_strategy")

    if run_type == "l":
        core = f"LIVE TRADING INITIALIZED - TRADING WITH"
    elif run_type == "b":
        core = f"BACKTEST RUN INITIALIZED - TESTING"
    elif run_type == "o":
        core = f"OPTIMIZATION RUN INITIALIZED - OPTIMIZING"
    else:
        raise ValueError(f"{run_type} is not recognized")

    core += f" [{type(trade_strategy).__name__}] WITH VOLUME STRATEGY [{type(volume_strategy).__name__}] -"

    return core


# Map labels to their formatters.
_FORMATTERS: Dict[Label, Formatter] = {
    Label.ORDER_FILLED:             _fmt_order_filled,
    Label.ORDER_REJECT:             _fmt_order_reject,
    Label.HEARTBEAT:                _fmt_heartbeat,
    Label.EXECUTION_ERR:            _fmt_execution_err,
    Label.PNL_SNAPSHOT:             _fmt_pnl_snapshot,
    Label.ORDER_CLOSED:             _fmt_order_closed,
    Label.SUMMARY:                  _fmt_summary,
    Label.LOGGER_ERROR:             _fmt_logger_error,
    Label.OPTIMIZATION_RESULT:      _fmt_optimization_result,
    Label.SETUP_COMPLETE:           _fmt_setup_complete,
    # 👉 Add: Label.NEW_LABEL: your_formatter
}

def _default_log_root() -> Path:
    # <repo>/src/utils/logger.py -> parents[1] == <repo>/src
    return Path(__file__).resolve().parents[2] / "logs"

def _new_session_name(prefix: str | None = None) -> str:
    # local time, filesystem-safe, unique to the ms
    now = datetime.now().astimezone()
    ts  = now.strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]  # ms precision
    return f"{prefix+'_' if prefix else ''}{ts}"


# --- 3) The async logger implementation --------------------------------------

class AsyncLogger:
    """
    Non-blocking logger with hardcoded label->formatter mapping.

    - Text events -> newline-delimited JSON in events.log (ts, label, text)
    - Figures/images -> saved under images/ and referenced in events.log
    - close() writes summary.html embedding the images
    - Logging calls are O(1) enqueue; I/O happens in a background thread
    - If the queue is full, events are dropped (configurable)
    """

    def __init__(
        self,
        root: str | Path | None = None,
        session_name: Optional[str] = None,
        log_dir_prefix= None,
        max_queue: int = 50000,
        drop_when_full: bool = True,
        flush_every: int = 25,
        log_trades: bool = True,
    ):
        name = session_name or _new_session_name(prefix=log_dir_prefix)          # e.g. 2025-08-08_16-21-03_247
        base = Path(root).resolve() if root else _default_log_root()  # <repo>/src/logs
        self.root = base
        self.session_dir = self.root / name
        self.images_dir = self.session_dir / "images"
        self.events_file = self.session_dir / "events.log"

        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self._q: "Queue[tuple[str, dict]]" = Queue(maxsize=max_queue)
        self._drop = drop_when_full
        self._stop = threading.Event()
        self._flush_every = max(1, flush_every)
        self._write_count = 0

        self._worker_t = threading.Thread(
            target=self._worker, name="AsyncLoggerWriter", daemon=True
        )
        self._worker_t.start()

        self.log_trades = log_trades

    # --- public API (non-blocking) ---

    def log(self, label: Label, *inputs: Any, **kwargs: Any) -> bool:
        """
        Queue a text event. Returns True if accepted, False if dropped.
        """
        if not self.log_trades and label in [Label.ORDER_FILLED, Label.ORDER_REJECT, Label.ORDER_CLOSED]:
            return True

        evt = {
            "ts": self._ts(),
            "label": label.name,   # store human-readable name
            "label_enum": label,   # keep enum for formatting in worker
            "inputs": inputs,
            "kwargs": kwargs,
        }
        try:
            self._q.put_nowait(("event", evt))
            return True
        except Full:
            if self._drop:
                return False
            self._q.put(("event", evt))
            return True

    def log_figure(
        self,
        label: Label,
        fig: Any,                # matplotlib Figure-like object with .savefig()
        filename: Optional[str] = None,
        description: Optional[str] = None,
        dpi: int = 120,
    ) -> bool:
        """
        Queue a figure save. Returns True if accepted, False if dropped.
        """
        evt = {
            "ts": self._ts(),
            "label": label.name,
            "fig": fig,
            "filename": filename,
            "description": description,
            "dpi": dpi,
        }
        try:
            self._q.put_nowait(("figure", evt))
            return True
        except Full:
            if self._drop:
                return False
            self._q.put(("figure", evt))
            return True

    def close(self, wait: bool = True) -> None:
        self._stop.set()
        if wait:
            self._worker_t.join(timeout=5)

    def __enter__(self) -> "AsyncLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- internals ---

    @staticmethod
    def _ts() -> str:
        # timezone-aware ISO timestamp with ms precision
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")

    @staticmethod
    def _safe_str(x: Any) -> str:
        try:
            return str(x)
        except Exception:
            return repr(x)

    def _format_event(self, label: Label, inputs: Iterable[Any], kwargs: Dict[str, Any]) -> str:
        f = _FORMATTERS.get(label)
        if f is None:
            # Unknown label => fast explicit failure (dev-time issue)
            return f"[UNREGISTERED LABEL {label.name}] inputs={inputs} {kwargs}"
        try:
            return f(*inputs, **kwargs)
        except Exception as e:
            return f"[formatter-error for {label.name}: {e!r}] raw={inputs} {kwargs}"

    def _worker(self) -> None:
        with self.events_file.open("a", encoding="utf-8") as f:
            while not (self._stop.is_set() and self._q.empty()):
                try:
                    kind, payload = self._q.get(timeout=0.05)
                except Empty:
                    continue

                try:
                    if kind == "event":
                        text = self._format_event(payload["label_enum"], payload["inputs"], payload["kwargs"])
                        rec = {"ts": payload["ts"], "label": payload["label"], "text": text}
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        self._bump_flush(f)

                    elif kind == "figure":
                        filename = payload["filename"] or f"{payload['label']}-{int(time.time()*1000)}.png"
                        out_path = self.images_dir / filename
                        payload["fig"].savefig(out_path, dpi=payload["dpi"], bbox_inches="tight")
                        rec = {
                            "ts": payload["ts"],
                            "label": payload["label"],
                            "image": str(out_path.relative_to(self.session_dir)),
                            "description": payload.get("description"),
                        }
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        self._bump_flush(f)
                except Exception as e:
                    f.write(json.dumps({
                        "ts": self._ts(),
                        "label": "LOGGER_ERROR",
                        "text": f"{type(e).__name__}: {e}"
                    }) + "\n")
                    self._bump_flush(f)
                finally:
                    self._q.task_done()

        # summary once at the end (no runtime cost on the hot path)
        try:
            self._write_summary()
        except Exception:
            pass

    def _bump_flush(self, file_obj) -> None:
        self._write_count += 1
        if self._write_count % self._flush_every == 0:
            file_obj.flush()

    def _write_summary(self) -> None:
        events = []
        try:
            with self.events_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        continue
        except FileNotFoundError:
            events = []

        parts = [
            "<!doctype html><meta charset='utf-8'>",
            "<title>Log Summary</title>",
            "<style>body{font-family:system-ui,sans-serif;margin:24px}"
            ".ts{color:#666;margin-right:6px}.label{font-weight:600}"
            ".event{margin:6px 0 14px}img{max-width:100%;height:auto;display:block;margin-top:6px}</style>",
            f"<h1>Session: {self.session_dir.name}</h1><hr>",
        ]

        for e in events:
            ts = e.get("ts", "")
            label = e.get("label", "")
            if "image" in e:
                desc = self._safe_str(e.get("description") or "")
                img_rel = e["image"]
                parts.append(
                    f"<div class='event'><span class='ts'>{ts}</span>"
                    f"<span class='label'>{label}</span>"
                    f"{f'<div>{desc}</div>' if desc else ''}"
                    f"<img src='{img_rel}' alt='{label}'></div>"
                )
            else:
                text = self._safe_str(e.get("text", ""))
                parts.append(
                    f"<div class='event'><span class='ts'>{ts}</span>"
                    f"<span class='label'>{label}:</span> {text}</div>"
                )

        (self.session_dir / "summary.html").write_text("\n".join(parts), encoding="utf-8")
