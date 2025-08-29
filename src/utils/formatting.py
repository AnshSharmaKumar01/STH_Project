# src/utils/formatting.py
from typing import Any, Mapping
import math

try:
    import numpy as _np
except Exception:  # numpy might not be installed in some envs
    _np = None


def _py(v: Any) -> Any:
    """Convert numpy scalars/bools to native Python types, leave others as-is."""
    if _np is not None:
        if isinstance(v, (_np.floating, _np.integer, _np.bool_)):
            return v.item()
    return v


def _money(x: Any) -> str:
    return f"{float(x):,.2f}"


def _num(x: Any) -> str:
    return f"{float(x):.2f}"


def _pct(x: Any) -> str:
    return f"{float(x):.2f}%"


def format_summary(summary: Mapping[str, Any], *, multiline: bool = True, indent: str = "  ") -> str:
    """
    Convert the portfolio `summary` dict into a human-readable string.

    Args:
        summary: dict produced by your backtest (keys: symbol, from, to, start_balance, ...)
        multiline: if True, returns a pretty multi-line block; otherwise a compact one-liner
        indent: indentation used for lines after the first when multiline=True

    Returns:
        str
    """
    s = {k: _py(v) for k, v in dict(summary).items()}

    sym   = s.get("symbol", "?")
    span_from = s.get("from", "?")
    span_to   = s.get("to", "?")

    start_bal = s.get("start_balance", 0.0)
    end_bal   = s.get("end_balance", 0.0)
    pnl       = s.get("net_profit", 0.0)

    trades    = int(s.get("trades", 0) or 0)
    win_rate  = s.get("win_rate_%", 0.0)
    avg_win   = s.get("avg_win", 0.0)
    avg_loss  = s.get("avg_loss", 0.0)

    pf        = s.get("profit_factor", "inf")
    dd        = s.get("max_drawdown_%", 0.0)
    sharpe    = s.get("sharpe", 0.0)

    lev       = s.get("leverage", 0)
    max_marg  = s.get("max_margin_used", 0.0)
    max_marg_pct = s.get("max_margin_usage_%", 0.0)

    # Profit factor can be the string "inf" in your dict
    if isinstance(pf, str) and pf.lower() == "inf":
        pf_str = "inf"
    else:
        try:
            pf_val = float(pf)
            pf_str = f"{pf_val:.2f}" if math.isfinite(pf_val) else "inf"
        except Exception:
            pf_str = str(pf)

    lines = [
        f"{sym} | {span_from} → {span_to}",
        f"Balance      : {_money(start_bal)} → {_money(end_bal)}  (PnL {float(pnl):+,.2f})",
        f"Trades/Win%  : {trades} / {_pct(win_rate)}",
        f"Avg Win/Loss : {_num(avg_win)} / {_num(avg_loss)}",
        f"PF/Sharpe    : {pf_str} / {_num(sharpe)}",
        f"Max DD       : {_pct(dd)}",
        f"Leverage/MM  : {lev:g}x | {_num(max_marg)} ({_num(max_marg_pct)}%)",
    ]

    if multiline:
        return "\n".join([lines[0]] + [indent + ln for ln in lines[1:]])

    # compact one-liner
    return (
        f"{sym} [{span_from}→{span_to}] | Bal {_money(start_bal)}→{_money(end_bal)} "
        f"(PnL {float(pnl):+,.2f}) | Trades {trades} Win {_pct(win_rate)} | "
        f"PF {pf_str} Sharpe {_num(sharpe)} | DD {_pct(dd)} | "
        f"Lev {lev:g}x MM {_num(max_marg)} ({_num(max_marg_pct)}%)"
    )

# src/utils/formatting.py  (add below format_summary)
from typing import Any, Mapping, Optional, Dict
import math
import json
from collections import OrderedDict

try:
    import numpy as _np
except Exception:
    _np = None


def _csv_safe_value(v: Any) -> Any:
    """Make a value safe for csv.DictWriter (no numpy scalars/NaN/Inf)."""
    # numpy scalars -> python
    if _np is not None and isinstance(v, _np.generic):
        v = v.item()

    # numbers: normalize NaN/Inf
    if isinstance(v, (int, float)):
        if isinstance(v, float):
            if math.isnan(v):
                return ""          # empty cell for NaN
            if math.isinf(v):
                return "inf" if v > 0 else "-inf"
        return v

    # containers: json-encode if they sneak in
    if isinstance(v, (list, tuple, dict)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)

    return v


def summary_to_csv_row(
    summary: Mapping[str, Any],
    *,
    params: Optional[Mapping[str, Any]] = None,
    score: Optional[float] = None,
    opt_index: Optional[int] = None,
    field_order: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Produce a flat, CSV-safe row dict.

    Args:
      summary: your backtest summary dict
      params: (optional) the parameter set tested
      score:  (optional) objective value for optimization
      opt_index: (optional) iteration number
      field_order: (optional) if provided, the output dict is returned
                   in this key order (missing keys become "")

    Returns:
      dict suitable for csv.DictWriter.writerow(...)
    """
    row: Dict[str, Any] = {}

    if opt_index is not None:
        row["optimization_number"] = int(opt_index)

    if score is not None:
        row["score"] = _csv_safe_value(score)

    if params:
        for k, v in params.items():
            row[f"param_{k}"] = _csv_safe_value(v)

    for k, v in summary.items():
        row[k] = _csv_safe_value(v)

    if field_order:
        # ensure stable column order
        ordered = OrderedDict()
        for k in field_order:
            ordered[k] = row.get(k, "")
        # include any extra keys not in field_order at the end
        for k, v in row.items():
            if k not in ordered:
                ordered[k] = v
        return ordered

    return row
