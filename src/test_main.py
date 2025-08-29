import MetaTrader5 as mt5

# === Shutdown ===
if not mt5.initialize(path=r"C:\Users\AnshKumar\Desktop\MT5\terminal64.exe"):
    print("initialize() failed, error code =", mt5.last_error())
import MetaTrader5 as mt5
import pandas as pd
import time

# === CONFIG ===
symbol = "EURUSD"
lot = 0.01
fast_ma = 5
slow_ma = 20
stoch_k = 14
stoch_d = 3
overbought = 80
oversold = 20
polling_interval = 60  # seconds
bars = 100


symbol_info = mt5.symbol_info(symbol)
if not symbol_info.visible:
    mt5.symbol_select(symbol, True)
filling_mode = symbol_info.filling_mode

print(f"Running strategy on {symbol} every {polling_interval} seconds...")

try:
    while True:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['fast_ma'] = df['close'].rolling(fast_ma).mean()
        df['slow_ma'] = df['close'].rolling(slow_ma).mean()
        low_min = df['low'].rolling(stoch_k).min()
        high_max = df['high'].rolling(stoch_k).max()
        df['%K'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['%D'] = df['%K'].rolling(stoch_d).mean()
        latest = df.iloc[-1]

        signal = None
        if (
            latest['fast_ma'] > latest['slow_ma']
            and latest['%K'] < oversold
            and latest['%K'] > latest['%D']
        ):
            signal = "buy"
        elif (
            latest['fast_ma'] < latest['slow_ma']
            and latest['%K'] > overbought
            and latest['%K'] < latest['%D']
        ):
            signal = "sell"

        open_positions = mt5.positions_get(symbol=symbol)
        if not open_positions and signal:
            price = (
                mt5.symbol_info_tick(symbol).ask if signal == "buy"
                else mt5.symbol_info_tick(symbol).bid
            )
            order_type = mt5.ORDER_TYPE_BUY if signal == "buy" else mt5.ORDER_TYPE_SELL

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 100123,
                "comment": f"MA+Stoch {signal}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[{latest['time']}] Executed {signal.upper()} @ {price}")
            else:
                print(f"[{latest['time']}] Trade failed - retcode: {result.retcode}")
        else:
            print(f"[{latest['time']}] No signal or position already open.")

        time.sleep(polling_interval)

except KeyboardInterrupt:
    print("Stopped manually.")

mt5.shutdown()
