"""Hybrid recommendation engine that enumerates every allowed Royal bet."""
from __future__ import annotations

from .adaptive_weights import AdaptiveWeights
from .analyzer import Analyzer
from .models import BET_COMBINATIONS, BetOption, GameResult, Recommendation

DEFAULT_ODDS = {
    "Пента-трик": 50.0,
    "Квадро-трик": 20.0,
    "Дабл-трик": 8.0,
    "Трик-дабл": 7.0,
    "Серия": 6.0,
    "Хет-трик": 3.0,
    "Дубль": 1.5,
}


class PredictionEngine:
    """Enumerate 42 bet variants and rank them through a weighted hybrid model."""

    def __init__(self, analyzer: Analyzer | None = None, weights: AdaptiveWeights | None = None, signal_threshold: float = 55.0) -> None:
        self.analyzer = analyzer or Analyzer()
        self.weights = weights or AdaptiveWeights()
        self.signal_threshold = signal_threshold

    def all_options(self) -> list[BetOption]:
        """Return all first-die and combination bet variants: 6 x 7 = 42."""
        return [BetOption(first_die, combo) for first_die in range(1, 7) for combo in BET_COMBINATIONS]

    def recommend(self, results: list[GameResult], top_n: int = 5) -> list[Recommendation]:
        """Rank all variants and return the strongest recommendations."""
        ranked: list[Recommendation] = []
        for option in self.all_options():
            scores = self.analyzer.score_option(option, results)
            rating = sum(scores[name] * self.weights.weights.get(name, 0.0) for name in scores)
            signal = max(0.0, min(100.0, rating))
            probability = signal / 100.0
            expected_value = probability * DEFAULT_ODDS[option.combination.value] - 1.0
            ranked.append(Recommendation(option, rating, signal, expected_value, scores))
        ranked.sort(key=lambda rec: (rec.rating, rec.expected_value), reverse=True)
        for index, rec in enumerate(ranked, start=1):
            rec.rank = index
        return ranked[:top_n]

    def skip_message(self, recommendations: list[Recommendation]) -> str | None:
        """Return a skip message when the best signal is below the configured threshold."""
        if not recommendations or recommendations[0].signal_strength < self.signal_threshold:
            return "Сильного сигнала нет. Рекомендуется пропустить партию."
        return None
