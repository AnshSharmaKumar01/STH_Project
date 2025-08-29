from abc import ABC, abstractmethod
from enum import Enum

from src.commons.trade import Trade

class Summary(ABC):
    """
    Abstract Strategy class, which is used to summarize the statistics over a certain period
    """

    @abstractmethod
    def summarize(self):
        pass


class DailySummary(Summary):
    """
    Summarizes the daily statistics.
    """
    def __init__(self, date, trades: [Trade]):
        """
        Takes a list of trades for a certain date, and summarizes the statistics for the day.
        :param date:
        :param p:
        """
        self.date = date
        self.daily_profit = None
        #TODO Implement the initialization, which takes in the list of trades for the day, and stores all the stats
        # Finish this by adding more relevant stats, like max profit, min profit, etc.

    def summarize(self):
        #TODO This method should summarize the statistics, and return them in a readable way. This output is what will
        # be in the final summary
        pass

class WeeklySummary(Summary):
    """
    Summarizes the weekly statistics.
    """
    def __init__(self, start_date, end_date, trades: [Trade]):
        """
        Takes a list of trades for a certain week, and summarizes the statistics for the week.
        :param valid_dates:
        :param trades:
        """
        self.start_date = start_date
        self.end_date = end_date
        self.weekly_profit = None
        #TODO Implement the initialization, which takes in the list of trades for the week, and stores all the stats
        # Finish this by adding more relevant stats, like max profit, min profit, etc.


    def summarize(self):
        #TODO This method should summarize the statistics, and return them in a readable way. This output is what will
        # be in the final summary
        pass


class MonthlySummary(Summary):
    """
    Summarizes the monthly statistics.
    """

    def __init__(self, valid_dates, trades: [Trade]):
        """
        Takes a list of trades for a certain month, and summarizes the statistics for the month.
        :param valid_dates:
        :param trades:
        """
        self.start_date = valid_dates[0]
        self.end_date = valid_dates[-1]
        self.monthly_profit = None
        # TODO Implement the initialization, which takes in the list of trades for the month, and stores all the stats
        # Finish this by adding more relevant stats, like max profit, min profit, etc.

    def summarize(self):
        # TODO This method should summarize the statistics, and return them in a readable way. This output is what will
        # be in the final summary
        pass

class SummaryType(Enum):
    DAILY   = ("Daily",   DailySummary)
    WEEKLY  = ("Weekly",  WeeklySummary)
    MONTHLY = ("Monthly", MonthlySummary)

    def __init__(self, label, cls):
        self.label = label
        self.cls   = cls