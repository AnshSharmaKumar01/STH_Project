from src.utils.helpers import strategy_select
from src.utils.log import log, Label
from src.sizing_strategies.loader import sizer_select

def setup(mode):
    selected_strategy = strategy_select()
    if selected_strategy is None:
        print("No strategy selected. Exiting.")
        quit()

    print(f"\nSelected Strategy: {type(selected_strategy).__name__}")

    sizer = sizer_select()
    if sizer is None:
        print("No volume strategy selected. Exiting.")
        quit()

    print(f"\nSelected sizer: {type(sizer).__name__}")

    log.log(Label.SETUP_COMPLETE,
            run_type=mode,
            trade_strategy=selected_strategy,
            volume_strategy=sizer)

    return selected_strategy, sizer