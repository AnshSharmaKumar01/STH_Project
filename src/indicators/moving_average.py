from abc import ABC, abstractmethod
from typing import Optional


class MovingAverage(ABC):

    def __init__(self, k: int) -> None:
        if k <= 0:
            raise ValueError("k must be greater than >= 1")
        self.k = int(k)

    @abstractmethod
    def push(self, x: float) -> float:
        """
        Pushes a new value into the MA, and returns the new MA value
        :param x:
        :return: New MA value, and updates the buffer
        """

    @abstractmethod
    def get(self):
        """
        Gets the current value of the MA
        :return:The current MA value
        """

class SimpleMovingAverage(MovingAverage):
    def __init__(self, k: int):
        super().__init__(k)
        self.buf = [0.0] * k     # circular buffer of last k values
        self.idx = 0             # next position to overwrite
        self.count = 0           # how many points seen (cap at k)
        self.sum = 0.0           # running sum of values currently in window

    def push(self, x: float) -> float:
        # value that will leave the window (0 if not full yet)
        old = self.buf[self.idx] if self.count == self.k else 0.0

        # update buffer and sum
        self.buf[self.idx] = x
        self.sum += x - old

        # advance ring index
        self.idx = (self.idx + 1) % self.k

        # increase count up to k
        if self.count < self.k:
            self.count += 1

        # average over current window size (less than k during warm-up)
        return self.sum / self.count

    def get(self):
        return self.sum / self.count

class ExponentialMovingAverage(MovingAverage):
    """EMA with smoothing; O(1) memory (no window storage)."""

    def __init__(self, k: int, alpha: Optional[float] = None):
        super().__init__(k)
        self.alpha = float(alpha) if alpha is not None else 2.0 / (self.k + 1.0)
        if not (0.0 < self.alpha <= 1.0):
            raise ValueError("alpha must be in (0, 1].")
        self._value: Optional[float] = None

    def push(self, x: float) -> float:
        if self._value is None:
            # common choices: set to first x, or average of first 'k' points
            self._value = x
        else:
            self._value = (1.0 - self.alpha) * self._value + self.alpha * x
        return self._value

    def get(self) -> float:
        if self._value is None:
            raise ValueError("EMA is empty; push at least one value first.")
        return self._value