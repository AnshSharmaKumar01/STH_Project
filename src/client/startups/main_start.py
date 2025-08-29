from __future__ import annotations

from src.client.startups import optimizer_start, backtest_start, live_start

def startup():
    mode = input("Select Mode (b=backtest / l=live / o=optimize / x=exit) : ").strip().lower()
    is_backtest = (mode == "b")
    is_optimize = (mode == "o")
    is_live = (mode == "l")
    is_exit = (mode == "x")

    try:
        if is_optimize:
            optimizer_start.startup(mode)
        elif is_backtest:
            backtest_start.startup(mode)
        elif is_live    :
            live_start.startup(mode)
        elif is_exit :
            exit(0)
        else:
            raise ValueError(f"'{mode}' is not supported.")
    except ValueError:
        print("\nWARNING: Invalid Mode Selected, try again\n")
        startup()
