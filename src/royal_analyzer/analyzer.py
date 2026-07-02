"""Lightweight statistical analysis models."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import BET_COMBINATIONS, BetOption, CombinationType, GameResult
from .statistics import combination_frequencies, recency, transitions, value_frequencies

MODEL_NAMES = ("frequency", "recency", "transitions", "local_trend")


@dataclass
class AnalyzerSnapshot:
    """Precomputed statistics used by the prediction engine and charts."""

    total_games: int
    windows: dict[str, dict[str, Counter]]
    recency: dict[str, dict[str, int | None]]
    transitions: dict[CombinationType, Counter[CombinationType]]


class Analyzer:
    """Build frequency, recency, transition, and local-trend scores from history."""

    def snapshot(self, results: list[GameResult]) -> AnalyzerSnapshot:
        """Compute reusable statistics for all configured history windows."""
        windows: dict[str, dict[str, Counter]] = {}
        for label, size in (("all", None), ("20", 20), ("50", 50), ("100", 100)):
            window = results if size is None else results[-size:]
            windows[label] = {"values": value_frequencies(window), "combinations": combination_frequencies(window)}
        return AnalyzerSnapshot(len(results), windows, recency(results), transitions(results))

    def score_option(self, option: BetOption, results: list[GameResult]) -> dict[str, float]:
        """Return normalized scores from each statistical model for a candidate bet."""
        if not results:
            return {name: 50.0 for name in MODEL_NAMES}
        snap = self.snapshot(results)
        combo = option.combination
        value = option.first_die
        total_rolls = max(snap.total_games * 5, 1)
        freq_value = snap.windows["all"]["values"][value] / total_rolls
        freq_combo = snap.windows["all"]["combinations"][combo] / max(snap.total_games, 1)
        frequency = min(100.0, (freq_value * 0.45 + freq_combo * 0.55) * 220)
        combo_age = snap.recency["combinations"].get(combo.value) or (snap.total_games + 1)
        value_age = snap.recency["values"].get(str(value)) or (snap.total_games + 1)
        recency_score = min(100.0, (combo_age / max(snap.total_games, 1) * 70) + (value_age / max(snap.total_games, 1) * 30))
        previous = results[-1].combination or CombinationType.NONE
        transition_counter = snap.transitions.get(previous, Counter())
        transition_total = sum(transition_counter.values()) or 1
        transition_score = transition_counter[combo] / transition_total * 100
        all_combo_rate = freq_combo
        local_combo_rate = snap.windows["20"]["combinations"][combo] / max(min(20, snap.total_games), 1)
        local_value_rate = snap.windows["20"]["values"][value] / max(min(20, snap.total_games) * 5, 1)
        trend_score = max(0.0, min(100.0, 50.0 + (local_combo_rate - all_combo_rate) * 200 + local_value_rate * 50))
        return {"frequency": frequency, "recency": recency_score, "transitions": transition_score, "local_trend": trend_score}
