"""Combination classification and statistical primitives."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence

from .models import CombinationType, GameResult


def classify_combination(dice: Sequence[int]) -> CombinationType:
    """Classify five dice according to Royal combination priority."""
    counts = sorted(Counter(dice).values(), reverse=True)
    unique = sorted(set(dice))
    if counts == [5]:
        return CombinationType.PENTA_TRICK
    if counts == [4, 1]:
        return CombinationType.QUADRO_TRICK
    if counts == [3, 2]:
        return CombinationType.TRICK_DOUBLE
    if counts == [2, 2, 1]:
        return CombinationType.DOUBLE_TRICK
    if len(unique) == 5 and unique[-1] - unique[0] == 4:
        return CombinationType.SERIES
    if counts == [3, 1, 1]:
        return CombinationType.HAT_TRICK
    if counts == [2, 1, 1, 1]:
        return CombinationType.DOUBLE
    return CombinationType.NONE


def value_frequencies(results: Sequence[GameResult]) -> Counter[int]:
    """Count every die value across a history window."""
    counter: Counter[int] = Counter()
    for result in results:
        counter.update(result.dice)
    return counter


def combination_frequencies(results: Sequence[GameResult]) -> Counter[CombinationType]:
    """Count combination types across a history window."""
    return Counter(result.combination or classify_combination(result.dice) for result in results)


def recency(results: Sequence[GameResult]) -> dict[str, dict[str, int | None]]:
    """Return how many completed parties ago each die value and combination appeared."""
    value_seen: dict[str, int | None] = {str(value): None for value in range(1, 7)}
    combo_seen: dict[str, int | None] = {combo.value: None for combo in CombinationType}
    for age, result in enumerate(reversed(results), start=1):
        for value in set(result.dice):
            value_seen[str(value)] = value_seen[str(value)] or age
        combo = result.combination or classify_combination(result.dice)
        combo_seen[combo.value] = combo_seen[combo.value] or age
    return {"values": value_seen, "combinations": combo_seen}


def transitions(results: Sequence[GameResult]) -> dict[CombinationType, Counter[CombinationType]]:
    """Build transition counters between consecutive completed combination types."""
    table: dict[CombinationType, Counter[CombinationType]] = defaultdict(Counter)
    for previous, current in zip(results, results[1:], strict=False):
        prev_combo = previous.combination or classify_combination(previous.dice)
        cur_combo = current.combination or classify_combination(current.dice)
        table[prev_combo][cur_combo] += 1
    return table
