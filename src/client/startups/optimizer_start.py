from __future__ import annotations

from src.client.startups import helpers as startup_helpers
from src.utils import helpers
from src.utils.formatting import format_summary
from src.utils.log import configure as log_configure

from src.commons import multitf_feed


def startup(mode: str):
    selected_strategy, sizer = startup_helpers.setup(mode)
    log_configure(log_trades=False)
    helpers.initialize_mt5()

    bars = multitf_feed.fetch_history_or_raise()

    from src.optimizer.runner import optimize_strategy
    winners = optimize_strategy(
        strategy_instance=selected_strategy,
        sizer_instance=sizer,
        bars_override=bars,
        # fitness=your_custom_fn_if_you_want,
        top_k=100,
        # max_evals=10,   # optional cap for very large grids
    )

    print("\n=== Optimization: top results ===")
    for i, r in enumerate(winners, 1):
        print(f"{i:>2}. score={r.score:.4f} params={r.params} "
              f"summary={format_summary(r.summary)}")
    # done
    exit(0)