from .position_sizing import PositionSizer, OrderContext

READABLE_FORMAT = "Sizing Strategy Template"

# What to Optimize
OPT_SPACE = [
    IntParam("a", 5, 40, 1),
    FloatParam("b", 1.0, 2.0, 0.1),
    CategoricalParam("c", ["1", "2"])
]

# What stays fixed
FIXED_PARAMS = {
    "d": 1,
}

# Default values for parameters
DEFAULT_PARAMS = {
    "a": 20,
    "b": 1.5,
    "c": "1",
    "d": 1,
}

def _rule_template(p: dict) -> bool:
    return int(p['a']) < float(p['b'])

RULES = [_rule_template]

class MartingaleSizer(PositionSizer):
    a: int = 20
    b: float = 1.5
    c: str = "1"
    d: int = 1

    def size(self, ctx: OrderContext) -> int:
        """
        This is called right before opening a position.

        :param ctx: This is the context of the order, it gives information like the type of order (long,short)
        and additonal information.
        :return: The size of the order. How many units to buy/sell
        """
        return None