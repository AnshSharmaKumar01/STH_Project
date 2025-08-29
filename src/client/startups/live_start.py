from __future__ import annotations

from src.utils.log import configure as log_configure
from src.client.startups import helpers as startup_helpers

def startup(mode: str):
    selected_strategy, sizer = startup_helpers.setup(mode)
    log_configure()
    # TODO IMPLEMENT LIVE RUNNER
    from src.client.trading_portfolio import TradingPortfolio
    portfolio = TradingPortfolio(strategy=selected_strategy, sizer=sizer)  # prepare live later
    portfolio.run()