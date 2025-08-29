class Trade:
    """
    Will help keep track of trades made, storing all important information inside this one object
    """
    def __init__(self, id, price, time, volume, type, sl=None, tp=None):
        self.open = True

        self.id = id
        self.open_price = price
        self.open_time = time
        self.volume = volume
        self.type = type
        self.sl = sl
        self.tp = tp

        self.close_price = None
        self.close_time = None
        self.trade_profit = None

    def close_trade(self, close_price, close_time):
        if self.open:
            self.open = False
            self.close_price = close_price
            self.close_time = close_time
            self.trade_profit = self.open_price - self.close_price
        else:
            print(f"ERROR - Trade with id -{self.id}- is already closed")

    def set_sl(self, sl):
        self.sl = sl

    def set_tp(self, tp):
        self.tp = tp