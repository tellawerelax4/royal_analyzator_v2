"""SQLite persistence layer."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

from .models import CombinationType, GameResult, PredictionStats, Recommendation
from .statistics import classify_combination


class Storage:
    """Store completed games, recommendations, weights, and virtual bank history."""

    def __init__(self, db_path: str | Path = "royal_analyzer.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
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
                sequence TEXT NOT NULL UNIQUE,
                sorted_combination TEXT NOT NULL,
                combination_type TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                first_die INTEGER NOT NULL,
                combination_type TEXT NOT NULL,
                rating REAL NOT NULL,
                signal_strength REAL NOT NULL,
                expected_value REAL NOT NULL,
                rank INTEGER NOT NULL,
                model_scores TEXT NOT NULL,
                checked INTEGER NOT NULL DEFAULT 0,
                success INTEGER,
                top3_success INTEGER
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
        self._migrate_schema()
        self.connection.commit()

    def _migrate_schema(self) -> None:
        """Add columns introduced after early scaffold versions."""
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(games)")}
        if "sequence" not in columns:
            self.connection.execute("ALTER TABLE games ADD COLUMN sequence TEXT")
            self.connection.execute("UPDATE games SET sequence = die1 || ' ' || die2 || ' ' || die3 || ' ' || die4 || ' ' || die5 WHERE sequence IS NULL")
            self.connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_games_sequence ON games(sequence)")
        rec_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(recommendations)")}
        if "group_id" not in rec_columns:
            self.connection.execute("ALTER TABLE recommendations ADD COLUMN group_id TEXT DEFAULT ''")
        if "top3_success" not in rec_columns:
            self.connection.execute("ALTER TABLE recommendations ADD COLUMN top3_success INTEGER")

    def add_game(self, result: GameResult) -> bool:
        """Insert one completed game; return False when it is a duplicate sequence."""
        combo = result.combination or classify_combination(result.dice)
        try:
            self.connection.execute(
                "INSERT INTO games(timestamp, die1, die2, die3, die4, die5, sequence, sorted_combination, combination_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (result.timestamp.isoformat(), *result.dice, result.sequence, result.sorted_combination, combo.value),
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

    def save_recommendations(self, recommendations: list[Recommendation], group_id: str | None = None) -> str:
        """Persist recommendation rankings made before a party starts and return their group id."""
        now = datetime.now(UTC).isoformat()
        group = group_id or now
        self.connection.executemany(
            "INSERT INTO recommendations(group_id, timestamp, first_die, combination_type, rating, signal_strength, expected_value, rank, model_scores) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(group, now, rec.option.first_die, rec.option.combination.value, rec.rating, rec.signal_strength, rec.expected_value, rec.rank, json.dumps(rec.model_scores, ensure_ascii=False)) for rec in recommendations],
        )
        self.connection.commit()
        return group

    def mark_recommendation_group(self, group_id: str, result: GameResult) -> None:
        """Mark a recommendation group as checked against a completed party."""
        actual = result.combination or classify_combination(result.dice)
        rows = self.connection.execute("SELECT id, rank, first_die, combination_type FROM recommendations WHERE group_id = ?", (group_id,)).fetchall()
        for row in rows:
            exact = int(row["rank"] == 1 and row["first_die"] == result.dice[0] and row["combination_type"] == actual.value)
            top3 = int(row["rank"] <= 3 and row["combination_type"] == actual.value)
            self.connection.execute("UPDATE recommendations SET checked = 1, success = ?, top3_success = ? WHERE id = ?", (exact, top3, row["id"]))
        self.connection.commit()

    def prediction_stats(self) -> PredictionStats:
        """Return aggregate top-1/top-3 hit statistics based on checked groups."""
        groups = self.connection.execute(
            "SELECT group_id, MAX(CASE WHEN rank = 1 THEN success ELSE 0 END) AS top1, MAX(top3_success) AS top3 FROM recommendations WHERE checked = 1 GROUP BY group_id ORDER BY MIN(id)"
        ).fetchall()
        stats = PredictionStats(total=len(groups))
        current = 0
        for row in groups:
            top1 = bool(row["top1"])
            top3 = bool(row["top3"])
            stats.top1_hits += int(top1)
            stats.top3_hits += int(top3)
            current = current + 1 if top1 else 0
            stats.best_streak = max(stats.best_streak, current)
        stats.current_streak = current
        return stats

    def save_weights(self, weights: dict[str, float]) -> None:
        """Upsert adaptive model weights."""
        now = datetime.now(UTC).isoformat()
        self.connection.executemany("INSERT OR REPLACE INTO model_weights(model, weight, updated_at) VALUES (?, ?, ?)", [(name, value, now) for name, value in weights.items()])
        self.connection.commit()

    def load_weights(self) -> dict[str, float]:
        """Load persisted model weights."""
        return {row["model"]: row["weight"] for row in self.connection.execute("SELECT model, weight FROM model_weights")}

    def save_virtual_bank(self, balance: float, profit: float, roi: float, drawdown: float) -> None:
        """Persist a virtual bank metric point for charts."""
        self.connection.execute("INSERT INTO virtual_bank(timestamp, balance, profit, roi, drawdown) VALUES (?, ?, ?, ?, ?)", (datetime.now(UTC).isoformat(), balance, profit, roi, drawdown))
        self.connection.commit()

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()
