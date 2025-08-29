from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class StrategyRisk:
    #Netting vs Hedging
    allow_hedging: bool = False

    #Pyramiding
    allow_pyramiding: bool = False
    max_layers: int = 1
    min_step_price: Optional[float] = None
