"""Self-adjusting model weights."""
from __future__ import annotations

from .analyzer import MODEL_NAMES
from .models import Recommendation, GameResult
from .statistics import classify_combination


class AdaptiveWeights:
    """Maintain and adapt hybrid model weights after every completed party."""

    def __init__(self, initial: dict[str, float] | None = None) -> None:
        self.weights = initial or {name: 1.0 / len(MODEL_NAMES) for name in MODEL_NAMES}

    def normalize(self) -> None:
        """Normalize weights so the sum is one."""
        total = sum(self.weights.values()) or 1.0
        self.weights = {name: max(0.05, value / total) for name, value in self.weights.items()}
        total = sum(self.weights.values())
        self.weights = {name: value / total for name, value in self.weights.items()}

    def adapt(self, recommendations: list[Recommendation], result: GameResult) -> dict[str, float]:
        """Reward models that gave higher scores to the actually observed combination."""
        actual = result.combination or classify_combination(result.dice)
        relevant = [rec for rec in recommendations if rec.option.combination == actual]
        if not relevant:
            return self.weights
        averages = {name: sum(rec.model_scores.get(name, 0.0) for rec in relevant) / len(relevant) for name in self.weights}
        best = max(averages, key=averages.get)
        for name in self.weights:
            self.weights[name] *= 1.05 if name == best else 0.98
        self.normalize()
        return self.weights
