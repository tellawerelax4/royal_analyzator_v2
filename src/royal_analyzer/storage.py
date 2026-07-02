"""SQLite persistence layer."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

from .models import BetOption, CombinationType, GameResult, Recommendation
from .statistics import classify_combination


class Storage:
    """Store completed games, recommendations, weights, and virtual bank history."""

    def __init__(self, db_path: str | Path = "royal_analyzer.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        """Create all application tables if they do not exist."""
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                die1 INTEGER NOT NULL, die2 INTEGER NOT NULL, die3 INTEGER NOT NULL,
                die4 INTEGER NOT NULL, die5 INTEGER NOT NULL,
                sorted_combination TEXT NOT NULL,
                combination_type TEXT NOT NULL,
                UNIQUE(die1, die2, die3, die4, die5, timestamp)
            );
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                first_die INTEGER NOT NULL,
                combination_type TEXT NOT NULL,
                rating REAL NOT NULL,
                signal_strength REAL NOT NULL,
                expected_value REAL NOT NULL,
                rank INTEGER NOT NULL,
                model_scores TEXT NOT NULL,
                checked INTEGER NOT NULL DEFAULT 0,
                success INTEGER
            );
            CREATE TABLE IF NOT EXISTS model_weights (
                model TEXT PRIMARY KEY,
                weight REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS virtual_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                balance REAL NOT NULL,
                profit REAL NOT NULL,
                roi REAL NOT NULL,
                drawdown REAL NOT NULL
            );
            """
        )
        self.connection.commit()

    def add_game(self, result: GameResult) -> bool:
        """Insert one completed game; return False when it is a duplicate."""
        combo = result.combination or classify_combination(result.dice)
        try:
            self.connection.execute(
                "INSERT INTO games(timestamp, die1, die2, die3, die4, die5, sorted_combination, combination_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (result.timestamp.isoformat(), *result.dice, result.sorted_combination, combo.value),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_games(self, limit: int | None = None) -> list[GameResult]:
        """Load games ordered by insertion time."""
        sql = "SELECT * FROM games ORDER BY id"
        params: tuple[int, ...] = ()
        if limit:
            sql = "SELECT * FROM (SELECT * FROM games ORDER BY id DESC LIMIT ?) ORDER BY id"
            params = (limit,)
        rows = self.connection.execute(sql, params).fetchall()
        return [GameResult(tuple(row[f"die{i}"] for i in range(1, 6)), datetime.fromisoformat(row["timestamp"]), CombinationType(row["combination_type"])) for row in rows]

    def save_recommendations(self, recommendations: list[Recommendation]) -> None:
        """Persist recommendation rankings made before a party starts."""
        now = datetime.now(UTC).isoformat()
        self.connection.executemany(
            "INSERT INTO recommendations(timestamp, first_die, combination_type, rating, signal_strength, expected_value, rank, model_scores) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(now, rec.option.first_die, rec.option.combination.value, rec.rating, rec.signal_strength, rec.expected_value, rec.rank, json.dumps(rec.model_scores, ensure_ascii=False)) for rec in recommendations],
        )
        self.connection.commit()

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()
