# STH Project
**short description of the project**

## Table of Contents [Incomplete]
**When done with the rest of the readme, give it to chat and make this**

## About
This repository contains code to aid with the development of trading bots. It makes implementing, backtesting, and 
deploying bots easier. To understand fully how the project works read below.

The project is fully in Python, but it can only be run on devices running Windows. The MetaTrader5 library only 
works on Windows devices.

## Installation

### Prerequisites
1. Python (3.13 recommended)
2. Windows 10+
3. MetaTrader5

### Clone the repo
```bash
git clone https://github.com/AnshSharmaKumar01/STH_Project.git
cd STH_Project
```
### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage [Incomplete]

### Running the project [Incomplete]
To run the project simply run:
```bash
python launch.py
```

When you run the project you will be prompted for which mode you want to run. The running modes are 
[Backtest](#backtest-mode), [Optimize](#optimize-mode), [Live](#live-mode). The initial prompt looks like:

```bash
Select Mode (b=backtest / l=live / o=optimize / x=exit) : b
```

Once you choose the mode, you need to select the trading strategy you want to use and the sizing strategy. The 
prompts for those look like:

```bash


Which Strategy would you like to use?
(1) Moving Average Crossover Scalping   [ma_crossover_scalping]
(2) Test Strategy   [tester_strategy]
(q) quit

Answer - 1

Selected Strategy: MACrossoverScalping

Which Volume Strategy (position sizer) would you like to use?
(1) Win Streak Sizer (+20% per win, cap 3)   [win_streak_sizer]
(2) Fixed Units (t)   [fixed_units]
(q) quit

Answer - 1

Selected sizer: WinStreakSizer
```

Once the strategies are selected, a confirmation is printed for which strategy you are running. After the setup is 
complete the mode will run and the outputs will be displayed. Which outputs are displayed depends on the mode you 
are running. 

#### Backtest mode
When running backtest mode, the software automatically backtests the strategy, and then prints out a summary of the 
relevant statistics of the run. The output would look like this:

```bash
=== Backtest Summary ===
symbol: EURUSD
from: 2025-06-11T10:11:00+00:00
to: 2025-06-27T23:58:00+00:00
start_balance: 3000.0
end_balance: 2540.8410199999585
net_profit: -459.15898000004154
trades: 169
win_rate_%: 34.91
avg_win: 15.58
avg_loss: -11.36
profit_factor: 0.74
max_drawdown_%: 17.8
sharpe: -7.66
max_margin_used: 40.15
max_margin_usage_%: 1.31
```

If you want to add or remove certain statistics from the summary, you can do that by editing the `_summarize()` 
method in the `src/client/testing-portfolio.py` file.

The backtest works by getting the historical tick values from the dates specified in the 
`src/settings/backtest_config.py` file. Keep in mind that the ticks are retrieved from MT5, so if the timeframe is 
out of range from what MT5 can provide, it will just retrieve what it can.

#### Optimize Mode
When running optimize mode, the software optimizes the parameters provided for the trading strategy. Currently, it 
does this via a gridsearch, but in the future I aim to add more efficient optimization models. Details on what 
parameters get optimized can be found in the [Adding New Trading Strategies](#adding-new-trading-strategies-incomplete) 
section. 

Currently only the trading strategies hyperparameters get optimized, but in the future optimizing sizing strategies 
will be added. When you run the optimize mode, and after the strategies are prompted, you should see each round 
being run, until it is finished and then a summary is printed.

```bash
Round 1 / 1277 finished
Round 2 / 1277 finished
Round 3 / 1277 finished
Round 4 / 1277 finished
...
Round 1277/1277 finished
```

Once all the rounds are done, top k results can be found in the location that is printed. For the strategy being 
optimized a csv file is made which contains the configuration of the top k configurations. 

The performance is measured by a fitness function. This function needs to be located in the `src/optimizer/runner.
py` file. To keep it organized, keep the fitness function method under the `default_fitness()` method. The k, for 
the top k results can also be changed when calling `optimize_strategy()`, since it is one of the parameters. This 
method is called in `src/client/startups/optmizer_start.py`, here the k can also be changed.

#### Live Mode [Incomplete]

CURRENTLY NOT IMPLEMENTED

### Adding New Trading Strategies
To add a new trading strategy, make sure to create a new python file, with the name of your strategy, and save it in 
`src/trading_strategies/`. You can follow the trading strategy template found in 
`src/strategy_templates/trading_strategy_template.py`, a simple trading strategy can be found in 
`src/trading_strategies/ma_crossover_scalping.py`. To ensure that the trading strategy works fully, the following 
need to be included:

1. `READABLE_FORMAT` is a **required** string that needs to be included, this is what will be printed during the 
   initial 
   prompt
2. To allow for full optimization functionality the following need to be included:
   1. `OPT_SPACE` is a **required** list of param objects. These are the parameters that are optimized. The 
      different parameter types can be found in `src/optimizer/space.py`. The 3 kinds of parameters are [IntParam](#intparam), 
      [FloatParam](#floatparam), and [CategoricalParam](#categoricalparam).
   2. `FIXED_PARAMS` is a **required** dictionary of fixed parameters. The keys are the names of the parameters, and 
      the value is the fixed value for them.
   3. `DEFAULT_PARAMS` is a **required** dictionary of the default values for every parameter. This should include 
      all the parameters, and their default values.
   4. `RULES` is a **required** list of rules. This list can be empty. A rule is a method that returns a boolean 
      value. The rules here are rules that the parameters should follow. For instance, if parameter a should always 
      be smaller than parameter b. Follow the format for the rules as in the template file.
3. The class should be named the name of the strategy, and should have all the parameters included. For a fully 
   functioning strategy class, the following need to be included:
   1. `RISK` is a **required** object `StrategyRisk`, found in `src/commons/risk.py`. This object contains information 
      about 
      what is and is not allowed during trading. Currently, it includes hedging and pyramiding.
   2. `on_bar()` is an **optional** method. This method is called whenever a new bar is introduced. This method is 
      useful for updating indicators such as MA.
   3. `decide()` is a **required** method. Here the logic for the position decision is made. It is recommended to 
      only include the decision logic here, and the updating of indicators/variables in `on_bar()`.
   4. `__post_init__` is an **optional** method. This method is called after the object is initialized. It is 
      recommended to initialize all the indicators here.
   5. `_post_feed_init` is an **optional** method. This method is called after the feed is initialized. In this 
      method, objects that need values from the feed should be initialized, such as MA.
4. `initialize_strategy(**params)` is a **required** method. This method should be at the bottom of the file, 
   outside the class. This method initializes the actual strategy given the parameters as input. Make sure that the 
   initialize follows the same structure as the template, with p. Make sure to also check if the parameters here 
   follow the rules, if not throw a `ValueError`


### Adding New Sizing Strategies
To add a new sizing strategy, make sure to create a new python file, with the name of your strategy, and save it in 
`src/sizing_strategies/`. You can follow the sizing strategy template found in 
`src/strategy_templates/sizing_strategy_template.py`, a simple sizing strategy can be found in 
`src/sizing_strategies/win_streak_sizer.py`. To ensure that the sizing strategy works fully, the following 
need to be included:

1. `READABLE_FORMAT` is a **required** string that needs to be included, this is what will be printed during the 
   initial prompt
2. To allow for full optimization functionality the following need to be included:
   1. `OPT_SPACE` is a **required** list of param objects. These are the parameters that are optimized. The 
      different parameter types can be found in `src/optimizer/space.py`. The 3 kinds of parameters are [IntParam](#intparam), 
      [FloatParam](#floatparam), and [CategoricalParam](#categoricalparam).
   2. `FIXED_PARAMS` is a **required** dictionary of fixed parameters. The keys are the names of the parameters, and 
      the value is the fixed value for them.
   3. `DEFAULT_PARAMS` is a **required** dictionary of the default values for every parameter. This should include 
      all the parameters, and their default values.
   4. `RULES` is a **required** list of rules. This list can be empty. A rule is a method that returns a boolean 
      value. The rules here are rules that the parameters should follow. For instance, if parameter a should always 
      be smaller than parameter b. Follow the format for the rules as in the template file.
3. The class should be named the name of the strategy, and should have all the parameters included. For a fully 
   functioning strategy class, the following need to be included:
   1. `size(ctx: OrderContext)` is a **required** method. This method is given the [OrderContext](#ordercontext) and
       then returns the size of the position.
4. `initialize_strategy(**params)` is a **required** method. This method should be at the bottom of the file, 
   outside the class. This method initializes the actual strategy given the parameters as input. Make sure that the 
   initialize follows the same structure as the template, with p. Make sure to also check if the parameters here 
   follow the rules, if not throw a `ValueError`

### Adding New Indicators
When adding new indicators, store them under `src/indicators/`. If there are variants of indicators (ie. MA, SMA, EMA), 
then keep them in one file. If the file is too large then create a new directory under `src/indicators/` and add the 
relevant files there.

## Features [Incomplete]

### OrderContext
Provides the context of the current order. The implementation can be seen below:

```python
@dataclass(frozen=True)
class OrderContext:
    symbol: str
    side: int                     # +1 long, -1 short (for the order being considered)
    price: float
    equity: float
    free_margin: float
    leverage: float
    position: Optional[object]    # DEPRECATED: None when multi-pos; kept for old sizers
    positions: Tuple[object, ...] # NEW: all open positions (immutable snapshot)
    trades: Tuple[object, ...]    # closed trades history
    feed: MultiTFFeedView
    bar: object
    layer: int = 1
```

### Optimization Parameters
To make optimizing easier, use the optimization parameters below.

#### IntParam
For parameters which are integers the `IntParam` object should be used. The implementation can be seen below:

```python
@dataclass(frozen=True)
class IntParam:
    name: str
    low: int
    high: int
    step: int = 1
    def values(self) -> Iterable[int]:
        return range(self.low, self.high + 1, self.step)
```
#### FloatParam
For parameters which are floats the `FloatParam` object should be used. The implementation can be seen below:

```python
@dataclass(frozen=True)
class FloatParam:
    name: str
    low: float
    high: float
    step: float
    def values(self) -> Iterable[float]:
        # safe step iteration
        v = self.low
        while v <= self.high + 1e-12:
            yield round(v, 10)
            v += self.step
```

#### CategoricalParam
For more categorical parameters, for instance the type of moving average, the `CategoricalParam` is used. The 
implemetation can be seen below: 
```python
@dataclass(frozen=True)
class CategoricalParam:
    name: str
    choices: Sequence[Any]
    def values(self) -> Iterable[Any]:
        return list(self.choices)
```

## Contributing
Contributions are welcome!
1. Fork the project
2. Create your own feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

## Contact

Ansh Sharma Kumar   - ansh.sharma.kumar01@gmail.com (Start the email with "STH PROJECT - " for faster responses)

Project Link        - https://github.com/AnshSharmaKumar01/STH_Project.git
