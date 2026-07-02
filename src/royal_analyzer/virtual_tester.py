"""Virtual betting tester for recommendations; it never interacts with the website."""
from __future__ import annotations

from dataclasses import dataclass

from .models import GameResult, Recommendation
from .prediction_engine import DEFAULT_ODDS
from .statistics import classify_combination


@dataclass
class VirtualMetrics:
    """Virtual bank performance metrics."""

    balance: float
    roi: float
    profit: float
    loss: float
    winrate: float
    max_drawdown: float
    average_profit: float
    bets: int


class VirtualTester:
    """Evaluate saved recommendations against real completed game outcomes."""

    def __init__(self, initial_bank: float = 1000.0, stake: float = 10.0, odds: dict[str, float] | None = None) -> None:
        self.initial_bank = initial_bank
        self.balance = initial_bank
        self.stake = stake
        self.odds = odds or DEFAULT_ODDS
        self.bets = 0
        self.wins = 0
        self.peak = initial_bank
        self.max_drawdown = 0.0
        self.total_profit = 0.0
        self.total_loss = 0.0

    def settle(self, recommendation: Recommendation, result: GameResult) -> float:
        """Settle one virtual bet and return net profit/loss."""
        self.bets += 1
        actual = result.combination or classify_combination(result.dice)
        if recommendation.option.combination == actual and recommendation.option.first_die == result.dice[0]:
            profit = self.stake * (self.odds[actual.value] - 1.0)
            self.wins += 1
            self.total_profit += profit
        else:
            profit = -self.stake
            self.total_loss += self.stake
        self.balance += profit
        self.peak = max(self.peak, self.balance)
        self.max_drawdown = max(self.max_drawdown, self.peak - self.balance)
        return profit

    def metrics(self) -> VirtualMetrics:
        """Return current ROI, drawdown, winrate, and average profit metrics."""
        invested = self.bets * self.stake
        profit = self.balance - self.initial_bank
        roi = (profit / invested * 100.0) if invested else 0.0
        return VirtualMetrics(self.balance, roi, self.total_profit, self.total_loss, (self.wins / self.bets * 100.0) if self.bets else 0.0, self.max_drawdown, profit / self.bets if self.bets else 0.0, self.bets)
