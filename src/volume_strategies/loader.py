# src/volume_strategies/loader.py
from __future__ import annotations
import importlib, pkgutil
from typing import Dict, List, Callable, Any

from .position_sizing import PositionSizer, FixedUnitsSizer   # base + fallback

def _discover() -> List[Dict[str, Any]]:
    """
    Find modules inside volume_strategies that define:
      - READABLE_FORMAT (str)
      - initialize_sizer() -> PositionSizer
    Skips the base module 'position_sizing'.
    """
    import src.volume_strategies as pkg
    items: List[Dict[str, Any]] = []

    for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if ispkg or modname.endswith(".position_sizing"):
            continue
        m = importlib.import_module(modname)
        label = getattr(m, "READABLE_FORMAT", None) or getattr(m, "SIZER_NAME", None)
        init  = getattr(m, "initialize_sizer", None)
        if isinstance(label, str) and callable(init):
            key = modname.rsplit(".", 1)[-1]
            items.append({"key": key, "label": label, "init": init})

    return items

def _order_with_fixed_last(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def is_fixed(x: Dict[str, Any]) -> bool:
        k = x["key"].lower(); l = x["label"].lower()
        return "fixed" in k or "fixed" in l or "tester" in k or "tester" in l
    fixed = [x for x in items if is_fixed(x)]
    others = [x for x in items if not is_fixed(x)]
    others.sort(key=lambda d: d["label"].lower())
    fixed.sort(key=lambda d: d["label"].lower())
    return others + fixed

def sizer_select(default_units: int | None = None) -> PositionSizer | None:
    """
    Prompt user to pick a position sizer by number/name.
    Adds a built-in 'Fixed Units' sizer (picked with 't') if none is present.
    """
    items = _discover()

    # Always have a fixed-units option available
    if default_units is None:
        try:
            from src import backtest_config as cfg
            default_units = int(getattr(cfg, "ORDER_SIZE_UNITS", 10_000))
        except Exception:
            default_units = 10_000

    if not any("fixed" in it["label"].lower() for it in items):
        items.append({
            "key": "fixed_units",
            "label": "Fixed Units",
            "init": (lambda du=default_units: FixedUnitsSizer(du)),
        })

    items = _order_with_fixed_last(items)

    if not items:
        print("No volume strategies found in `volume_strategies/`.")
        return None

    # locate tester/fixed index
    tester_idx = next(
        (i for i, s in enumerate(items)
         if "fixed" in s["key"].lower() or "fixed" in s["label"].lower() or "tester" in s["label"].lower()),
        None
    )

    # menu
    lines = ["\nWhich Volume Strategy (position sizer) would you like to use?"]
    for i, s in enumerate(items, 1):
        suffix = " (t)" if tester_idx is not None and (i-1) == tester_idx else ""
        lines.append(f"({i}) {s['label']}{suffix}   [{s['key']}]")
    lines.append("(q) quit")
    prompt = "\n".join(lines) + "\n\nAnswer - "

    while True:
        choice = input(prompt).strip()
        if choice.lower() in {"q", "quit", "exit"}:
            return None
        if choice.lower() == "t" and tester_idx is not None:
            return items[tester_idx]["init"]()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]["init"]()

        choice_l = choice.lower()
        matches = [s for s in items if choice_l == s["key"].lower() or choice_l in s["label"].lower()]
        if len(matches) == 1:
            return matches[0]["init"]()
        elif len(matches) > 1:
            print("Ambiguous; matches:", ", ".join(m["label"] for m in matches))
        else:
            print("Invalid selection, try again.")
