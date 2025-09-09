from __future__ import annotations
import importlib, pkgutil
from typing import List, Dict

import MetaTrader5 as mt5


def discover_strategies() -> List[Dict]:
    """
    Finds every module in `trading_strategies` that defines:
      - READABLE_FORMAT (str)
      - initialize_strategy()  (callable)
    Returns a list of dicts: {key, label, init}
    """
    import src.trading_strategies as pkg  # the package: src/trading_strategies/__init__.py must exist
    found = []
    for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if ispkg:
            continue
        module = importlib.import_module(modname)
        label = getattr(module, "READABLE_FORMAT", None)
        init  = getattr(module, "initialize_strategy", None)
        if isinstance(label, str) and callable(init):
            key = modname.rsplit(".", 1)[-1]  # file name without package
            found.append({"key": key, "label": label, "init": init})
    # nice, stable ordering
    found.sort(key=lambda d: d["label"].lower())
    return found

def strategy_select():
    """
    Prompts the user to pick a strategy by number or name and runs its init.
    Add a new file with READABLE_FORMAT + initialize_strategy() and it just appears.
    """
    strategies = discover_strategies()
    if not strategies:
        print("No trading_strategies found in `trading_strategies/`.")
        return None

    lines = ["\nWhich Strategy would you like to use?"]
    for i, s in enumerate(strategies, 1):
        lines.append(f"({i}) {s['label']}   [{s['key']}]")
    lines.append("(q) quit")
    prompt = "\n".join(lines) + "\n\nAnswer - "

    while True:
        choice = input(prompt).strip()
        if choice.lower() in {"q", "quit", "exit"}:
            return None
        # numeric choice
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(strategies):
                return strategies[idx]["init"]()
        # match by key or substring of label
        matches = [s for s in strategies
                   if choice.lower() == s["key"].lower()
                   or choice.lower() in s["label"].lower()]
        if len(matches) == 1:
            return matches[0]["init"]()
        elif len(matches) > 1:
            print("Ambiguous; matches:", ", ".join(m["label"] for m in matches))
        else:
            print("Invalid selection, try again.")

def initialize_mt5(path=r"C:\Users\AnshKumar\Desktop\MT5\terminal64.exe"):
    terminal_info = mt5.terminal_info()
    if terminal_info is None:
        if not mt5.initialize():
            print("ERROR - MT5 not in the default location.")
            if not mt5.initialize(path=path):
                print("initialize() failed, error code =", mt5.last_error())
                print("Go to src/utils/helpers.py and change the default path in the initialize_mt5 method")
                quit()

def resolve_timeframe(tf):
    """
    Accepts:
      - MT5 constants (already fine),
      - strings like 'M1','M5','M15','M30','H1','H4','D1','W1','MN1',
      - integers in minutes (1,5,15,30,60,240,1440).
    Returns an MT5 timeframe constant.
    """
    if isinstance(tf, int):
        by_minutes = {
            1: mt5.TIMEFRAME_M1,
            3: mt5.TIMEFRAME_M3 if hasattr(mt5, "TIMEFRAME_M3") else mt5.TIMEFRAME_M1,
            5: mt5.TIMEFRAME_M5,
            15: mt5.TIMEFRAME_M15,
            30: mt5.TIMEFRAME_M30,
            60: mt5.TIMEFRAME_H1,
            240: mt5.TIMEFRAME_H4,
            1440: mt5.TIMEFRAME_D1,
        }
        return by_minutes.get(tf, mt5.TIMEFRAME_M1)

    if isinstance(tf, str):
        tf = tf.strip().upper()
        const = getattr(mt5, f"TIMEFRAME_{tf}", None)
        if const is not None:
            return const
        # allow '1', '5', '15' as minutes in string form
        if tf.isdigit():
            return resolve_timeframe(int(tf))
    # assume it is already a valid MT5 constant
    return tf

def tf_seconds(tf: int) -> int:
    if tf == mt5.TIMEFRAME_M1:  return 60
    if tf == mt5.TIMEFRAME_M5:  return 300
    if tf == mt5.TIMEFRAME_M15: return 900
    if tf == mt5.TIMEFRAME_M30: return 1800
    if tf == mt5.TIMEFRAME_H1:  return 3600
    if tf == mt5.TIMEFRAME_H4:  return 14400
    if tf == mt5.TIMEFRAME_D1:  return 86400
    raise ValueError(f"Unsupported timeframe: {tf}")

def tf_minutes(tf: int) -> int:
    if tf == mt5.TIMEFRAME_M1:  return 1
    if tf == mt5.TIMEFRAME_M5:  return 5
    if tf == mt5.TIMEFRAME_M15: return 15
    if tf == mt5.TIMEFRAME_M30: return 30
    if tf == mt5.TIMEFRAME_H1:  return 60
    if tf == mt5.TIMEFRAME_H4:  return 240
    if tf == mt5.TIMEFRAME_D1:  return 1440
    raise ValueError(f"Unsupported timeframe: {tf}")