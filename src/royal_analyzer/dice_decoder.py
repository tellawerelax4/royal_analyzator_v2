"""DOM-only dice decoding helpers."""
from __future__ import annotations

import re
from collections.abc import Iterable

Coordinate = tuple[int, int]

DIE_MAP: dict[frozenset[Coordinate], int] = {
    frozenset({(2, 2)}): 1,
    frozenset({(1, 1), (3, 3)}): 2,
    frozenset({(1, 1), (2, 2), (3, 3)}): 3,
    frozenset({(1, 1), (1, 3), (3, 1), (3, 3)}): 4,
    frozenset({(1, 1), (1, 3), (2, 2), (3, 1), (3, 3)}): 5,
    frozenset({(1, 1), (1, 3), (2, 1), (2, 3), (3, 1), (3, 3)}): 6,
}
GRID_RE = re.compile(r"grid-area\s*:\s*(\d+)\s*/\s*(\d+)", re.I)


def decode_die(coordinates: Iterable[Coordinate]) -> int:
    """Decode pip coordinates from a 3x3 HTML die into a value from 1 to 6."""
    key = frozenset((int(row), int(column)) for row, column in coordinates)
    if key not in DIE_MAP:
        raise ValueError(f"Unknown die coordinate pattern: {sorted(key)}")
    return DIE_MAP[key]


def parse_grid_area(style: str) -> Coordinate | None:
    """Extract a `(row, column)` coordinate from a CSS grid-area declaration."""
    match = GRID_RE.search(style or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))
