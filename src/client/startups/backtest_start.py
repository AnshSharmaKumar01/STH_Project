from __future__ import annotations

from src.utils.log import configure as log_configure
from src.client.startups import helpers as startup_helpers

def startup(mode: str):
    selected_strategy, sizer = startup_helpers.setup(mode)
    log_configure()
    from src.client.testing_portfolio import TestingPortfolio
    portfolio = TestingPortfolio(strategy=selected_strategy, sizer=sizer, allow_window_adjust=True)  # <-- pass it in
    summary = portfolio.run()
    print("\n=== Backtest Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")