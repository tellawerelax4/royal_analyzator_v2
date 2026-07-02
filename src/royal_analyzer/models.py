"""Shared data models for Royal Analyzer Pro."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any


class CombinationType(StrEnum):
    """Supported Royal five-dice combination labels."""

    PENTA_TRICK = "Пента-трик"
    QUADRO_TRICK = "Квадро-трик"
    DOUBLE_TRICK = "Дабл-трик"
    TRICK_DOUBLE = "Трик-дабл"
    SERIES = "Серия"
    HAT_TRICK = "Хет-трик"
    DOUBLE = "Дубль"
    NONE = "Нет комбинации"


BET_COMBINATIONS: tuple[CombinationType, ...] = (
    CombinationType.PENTA_TRICK,
    CombinationType.QUADRO_TRICK,
    CombinationType.DOUBLE_TRICK,
    CombinationType.TRICK_DOUBLE,
    CombinationType.SERIES,
    CombinationType.HAT_TRICK,
    CombinationType.DOUBLE,
)


@dataclass(frozen=True)
class GameResult:
    """A completed Royal party with exactly five dice."""

    dice: tuple[int, int, int, int, int]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    combination: CombinationType | None = None

    @property
    def sorted_combination(self) -> str:
        """Return a normalized sorted dice string for duplicate detection and storage."""
        return " ".join(str(value) for value in sorted(self.dice))

    @property
    def sequence(self) -> str:
        """Return dice in observed order."""
        return " ".join(str(value) for value in self.dice)


@dataclass(frozen=True)
class BetOption:
    """A candidate bet checked by the prediction engine."""

    first_die: int
    combination: CombinationType


@dataclass
class Recommendation:
    """A ranked recommendation with model scores and expected value."""

    option: BetOption
    rating: float
    signal_strength: float
    expected_value: float
    model_scores: dict[str, float]
    rank: int = 0


@dataclass
class PredictionStats:
    """Aggregated prediction hit statistics for the GUI."""

    total: int = 0
    top1_hits: int = 0
    top3_hits: int = 0
    best_streak: int = 0
    current_streak: int = 0

    @property
    def top1_rate(self) -> float:
        """Return top-1 hit rate in percents."""
        return (self.top1_hits / self.total * 100.0) if self.total else 0.0

    @property
    def top3_rate(self) -> float:
        """Return top-3 hit rate in percents."""
        return (self.top3_hits / self.total * 100.0) if self.total else 0.0


JsonDict = dict[str, Any]
