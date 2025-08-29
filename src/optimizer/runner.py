from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Callable, List, Tuple, Optional
import importlib
import math
import csv
from pathlib import Path

from src.optimizer.space import grid, obeys, grid_size
from src.utils.formatting import format_summary
from src.utils.log import log, Label, get_current_log_dir  # get_current_log_dir -> helper in your logger that returns the active session dir

# Fitness function type: gets backtest summary; returns higher-is-better score
FitnessFn = Callable[[Dict[str, Any]], float]

# at top of runner.py
import time
import sys

def _fmt_eta(elapsed, i, n):
    if i == 0:
        return "ETA --:--"
    rate = elapsed / i
    remaining = rate * (n - i)
    mm, ss = divmod(int(remaining), 60)
    return f"ETA {mm:02d}:{ss:02d}"


@dataclass(frozen=True)
class OptimizeResult:
    params: Dict[str, Any]
    score: float
    summary: Dict[str, Any]

def default_fitness(summary: Dict[str, Any]) -> float:
    # Be robust to missing keys
    profit = summary.get("profit") or summary.get("net_profit") or (
        float(summary.get("final_balance", 0)) - float(summary.get("starting_balance", 0))
    )
    # penalize drawdown if available
    dd = float(summary.get("max_drawdown", 0.0))
    return float(profit)

def _module_for_strategy_instance(strategy_obj) -> Any:
    modname = strategy_obj.__class__.__module__
    return importlib.import_module(modname)

def optimize_strategy(
    strategy_instance,
    sizer_instance,
    fitness: FitnessFn = default_fitness,
    bars_override=None,
    top_k: int = 20,
    max_evals: Optional[int] = None,
) -> List[OptimizeResult]:
    """
    Discover the space/rules from the strategy's module and run a grid search.
    - strategy_instance: the selected strategy (used to find its module + defaults)
    - sizer_instance: current position sizer (used in each backtest)
    - bars_override: reuse same historical bars for speed (optional)
    - fitness(summary)->float: higher is better
    - max_evals: truncate the grid if huge (optional)
    """
    mod = _module_for_strategy_instance(strategy_instance)

    # Strategy module must expose:
    #   OPT_SPACE: list of Param objects
    #   FIXED_PARAMS: dict of non-optimizable defaults
    #   RULES: list[callable(params)->bool]
    #   initialize_strategy(**params) -> Strategy
    OPT_SPACE = getattr(mod, "OPT_SPACE", [])
    FIXED_PARAMS = getattr(mod, "FIXED_PARAMS", {})
    RULES = getattr(mod, "RULES", [])

    if not hasattr(mod, "initialize_strategy"):
        raise RuntimeError(f"{mod.__name__} must define initialize_strategy(**params)")

    candidates = []
    optimization_grid = grid(OPT_SPACE)
    n = grid_size(OPT_SPACE, RULES)
    for i, p in enumerate(optimization_grid, start=1):
        if max_evals and i > max_evals:
            break
        params = {**FIXED_PARAMS, **p}
        if not obeys(RULES, params):
            continue

        # Build fresh strategy with these params
        strat = mod.initialize_strategy(**params)

        # Run backtest with current sizer
        from src.client.testing_portfolio import TestingPortfolio
        portfolio = TestingPortfolio(strategy=strat, sizer=sizer_instance)
        summary = portfolio.run(history=bars_override)

        sc = fitness(summary)
        candidates.append(OptimizeResult(params=params, score=sc, summary=summary))

        log.log(Label.OPTIMIZATION_RESULT, eval_num=i, score=sc, params=params, summary=summary)
        print(f"Round {i} / {n} finished")

    # Rank
    candidates.sort(key=lambda r: r.score, reverse=True)
    winners = candidates[:top_k]

    # ... inside optimize_strategy(...)

    try:
        outdir = get_current_log_dir()
        OutDirPath = Path(outdir)
        outpath = Path.joinpath(OutDirPath, "Optimization Results") / f"{mod.READABLE_FORMAT}.csv"
        print(outpath)

        if winners:
            # preserve insertion order of dicts as provided by the strategy
            param_keys = list(winners[0].params.keys())
            summary_keys = list(winners[0].summary.keys())
        else:
            param_keys = [p.name for p in OPT_SPACE]
            summary_keys = []

        with outpath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["rank", "score", *param_keys, *summary_keys])

            def _csvify(v):
                # make numpy/scalars/datetimes CSV-safe without changing order
                try:
                    import numpy as np
                    if isinstance(v, (np.floating, np.integer)):
                        v = v.item()
                    elif isinstance(v, np.bool_):
                        v = bool(v)
                except Exception:
                    pass
                if v is None:
                    return ""
                if isinstance(v, float):
                    if math.isnan(v):
                        return ""
                    if math.isinf(v):
                        return "inf" if v > 0 else "-inf"
                if hasattr(v, "isoformat"):
                    try:
                        return v.isoformat()
                    except Exception:
                        pass
                return v

            for rank, r in enumerate(winners, start=1):
                row = [
                    rank,
                    _csvify(r.score),
                    *[_csvify(r.params[k]) for k in param_keys],
                    *[_csvify(r.summary[k]) for k in summary_keys],
                ]
                writer.writerow(row)

        log.log(Label.SUMMARY, f"optimizer results -> {outpath}")
    except Exception as e:
        log.log(Label.LOGGER_ERROR, f"failed to write optimizer CSV: {e!r}")

    return winners


