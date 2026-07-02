"""Application orchestration for live parsing, storage, prediction, and testing."""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from .adaptive_weights import AdaptiveWeights
from .analyzer import Analyzer
from .collector import SeleniumCollector
from .keep_alive import KeepAlive
from .models import GameResult, Recommendation
from .prediction_engine import PredictionEngine
from .storage import Storage
from .virtual_tester import VirtualTester

LOGGER = logging.getLogger(__name__)


class RoyalAnalyzerController:
    """Coordinate the live Selenium collector with persistence and analysis services."""

    def __init__(self, storage: Storage | None = None, selectors_path: str = "selectors.json") -> None:
        self.storage = storage or Storage()
        weights = self.storage.load_weights()
        self.adaptive_weights = AdaptiveWeights(weights or None)
        self.engine = PredictionEngine(Analyzer(), self.adaptive_weights)
        self.virtual_tester = VirtualTester()
        self.selectors_path = selectors_path
        self.collector: SeleniumCollector | None = None
        self.keep_alive: KeepAlive | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.last_recommendations: list[Recommendation] = []
        self.last_group_id: str | None = None
        self.listeners: list[Callable[[str], None]] = []
        self.last_error: str | None = None

    def add_listener(self, listener: Callable[[str], None]) -> None:
        """Register a text event listener for GUI logs."""
        self.listeners.append(listener)

    def emit(self, message: str) -> None:
        """Log and broadcast a controller event."""
        LOGGER.info(message)
        for listener in self.listeners:
            listener(message)

    def start(self, headless: bool = False, keep_alive_enabled: bool = True) -> None:
        """Start Selenium collection in a background thread."""
        if self._thread and self._thread.is_alive():
            self.emit("Парсер уже запущен")
            return
        self._stop.clear()
        self.last_error = None
        self.build_recommendations(save=True)
        self.collector = SeleniumCollector(self.selectors_path, poll_interval=0.5, headless=headless)
        self._thread = threading.Thread(target=self._run_collector, args=(keep_alive_enabled,), daemon=True)
        self._thread.start()
        self.emit("Запуск автоматического парсинга")

    def _run_collector(self, keep_alive_enabled: bool) -> None:
        """Background collector loop with debug capture delegated to SeleniumCollector."""
        assert self.collector is not None
        try:
            driver = self.collector.start_driver()
            self.collector.analyze_structure()
            self.keep_alive = KeepAlive(driver, enabled=keep_alive_enabled)
            self.keep_alive.start()
            self.emit("Selenium подключён, DOM-история читается каждые 500 мс")
            while not self._stop.is_set():
                for result in self.collector.poll_once():
                    self.handle_result(result)
                self._stop.wait(self.collector.poll_interval)
        except Exception as exc:
            LOGGER.exception("Live collector failed")
            self.last_error = str(exc)
            self.emit(f"Ошибка парсера: {exc}. Если браузер не стартует в Linux, установите системные библиотеки Chrome/Qt (например libatk, libnss3, libxkbcommon, libGL) или запустите на рабочей desktop-системе.")
            self.emit(f"Ошибка парсера: {exc}")
        finally:
            if self.keep_alive:
                self.keep_alive.stop()
            if self.collector:
                self.collector.close()
            self.emit("Парсер остановлен")

    def is_running(self) -> bool:
        """Return True while the background parser thread is alive."""
        return bool(self._thread and self._thread.is_alive())

    def stop(self) -> None:
        """Request live collection stop."""
        self._stop.set()

    def build_recommendations(self, save: bool = True) -> list[Recommendation]:
        """Build TOP-5 recommendations from stored history and optionally persist them."""
        games = self.storage.list_games()
        recommendations = self.engine.recommend(games)
        self.last_recommendations = recommendations
        if save and recommendations:
            self.last_group_id = self.storage.save_recommendations(recommendations)
        skip = self.engine.skip_message(recommendations)
        if skip:
            self.emit(skip)
        elif recommendations:
            best = recommendations[0]
            self.emit(f"Рекомендация: кубик {best.option.first_die}, {best.option.combination.value}, сигнал {best.signal_strength:.0f}%")
        return recommendations

    def handle_result(self, result: GameResult) -> None:
        """Store a new completed party, settle previous prediction, adapt weights, and prepare the next forecast."""
        inserted = self.storage.add_game(result)
        if not inserted:
            return
        self.emit(f"Новая партия: {result.sequence} / {result.combination.value if result.combination else '—'}")
        if self.last_group_id:
            self.storage.mark_recommendation_group(self.last_group_id, result)
        if self.last_recommendations:
            self.adaptive_weights.adapt(self.last_recommendations, result)
            self.storage.save_weights(self.adaptive_weights.weights)
            profit = self.virtual_tester.settle(self.last_recommendations[0], result)
            metrics = self.virtual_tester.metrics()
            self.storage.save_virtual_bank(metrics.balance, profit, metrics.roi, metrics.max_drawdown)
            self.emit(f"Виртуальный тест: {'+' if profit >= 0 else ''}{profit:.2f}, банк {metrics.balance:.2f}, ROI {metrics.roi:.2f}%")
        self.build_recommendations(save=True)
