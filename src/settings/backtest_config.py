from datetime import datetime, timezone
import MetaTrader5 as mt5

AUTO_ADJUST_HISTORY_WINDOW = True
INITIAL_BALANCE     = 3000
SYMBOL              = 'EURUSD'
TIMEFRAME           = mt5.TIMEFRAME_M1
DATE_START          = datetime(2025, 7, 25, tzinfo=timezone.utc)
DATE_END            = datetime(2025, 7, 30, tzinfo=timezone.utc)
WARMUP_BARS         = 200
ORDER_SIZE_UNITS    = 10_000
SPREAD_POINTS       = 10
SLIPPAGE_POINTS     = 2
COMMISSION_PER_LOT  = 7.0
EXECUTION_MODE      = "next_open"       # or "close"
LEVERAGE            = 500
ALLOW_HEDGING       = True        # True: long & short can coexist. False: netting (opposite side closes).
CLOSE_POLICY        = "fifo"      # how partial closes pick entries: "fifo" or "lifo"

