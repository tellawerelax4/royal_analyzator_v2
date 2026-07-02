"""PySide6 dark desktop interface for Royal Analyzer Pro."""
from __future__ import annotations

from collections import Counter

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QLabel, QListWidget, QMainWindow, QPushButton, QSplitter, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .controller import RoyalAnalyzerController
from .models import GameResult
from .storage import Storage


class MainWindow(QMainWindow):
    """Main two-panel dashboard with live parsing controls, stats, recommendations, and charts."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QMainWindow, QSplitter, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .prediction_engine import PredictionEngine
from .storage import Storage
from .virtual_tester import VirtualTester


class MainWindow(QMainWindow):
    """Main two-panel dashboard with status, recommendations, stats, bank, and charts."""

    def __init__(self, storage: Storage | None = None) -> None:
        super().__init__()
        self.storage = storage or Storage()
        self.controller = RoyalAnalyzerController(self.storage)
        self.controller.add_listener(self.add_event)
        self.pending_events: list[str] = []
        self.setWindowTitle("Royal Analyzer Pro")
        self.resize(1400, 820)
        self.setStyleSheet("QWidget { background: #111827; color: #e5e7eb; } QLabel { font-size: 14px; } QListWidget { background: #1f2937; } QPushButton { background: #2563eb; padding: 8px; border-radius: 4px; }")
        self.connection_label = QLabel("Статус подключения: не подключено")
        self.parser_label = QLabel("Статус парсера: остановлен")
        self.keep_alive_label = QLabel("KeepAlive: включён")
        self.games_label = QLabel("Количество партий: 0")
        self.last_result_label = QLabel("Последний результат: —")
        self.best_label = QLabel("Лучшая рекомендация: ожидание данных")
        self.weights_label = QLabel("Веса алгоритмов: —")
        self.stats_label = QLabel("Статистика прогнозов: —")
        self.bank_label = QLabel("Виртуальный банк: 1000.00 | ROI: 0.00%")
        self.history_list = QListWidget()
        self.event_log = QListWidget()
        self.recommendation_list = QListWidget()
        self.headless_box = QCheckBox("Headless Selenium")
        self.keep_alive_box = QCheckBox("KeepAlive")
        self.keep_alive_box.setChecked(True)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, 100.0)
        self.threshold.setValue(self.controller.engine.signal_threshold)
        self.threshold.setSuffix("% порог")
        self.engine = PredictionEngine()
        self.tester = VirtualTester()
        self.setWindowTitle("Royal Analyzer Pro")
        self.resize(1280, 760)
        self.setStyleSheet("QWidget { background: #111827; color: #e5e7eb; } QLabel { font-size: 14px; } QListWidget { background: #1f2937; }")
        self.left_log = QListWidget()
        self.right_log = QListWidget()
        self.best_label = QLabel("Лучшая рекомендация: ожидание данных")
        self.bank_label = QLabel("Виртуальный банк: 1000.00 | ROI: 0.00%")
        self.figure = Figure(facecolor="#111827")
        self.canvas = FigureCanvas(self.figure)
        self._build_layout()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

    def _build_layout(self) -> None:
        """Construct left status and right recommendation panels."""
        splitter = QSplitter()
        left = QWidget(); left_layout = QVBoxLayout(left)
        start_button = QPushButton("Старт автоматического парсинга")
        stop_button = QPushButton("Стоп")
        forecast_button = QPushButton("Сформировать прогноз")
        start_button.clicked.connect(self.start_parser)
        stop_button.clicked.connect(self.stop_parser)
        forecast_button.clicked.connect(self.manual_forecast)
        for widget in (self.connection_label, self.parser_label, self.keep_alive_label, self.games_label, self.last_result_label, self.headless_box, self.keep_alive_box, start_button, stop_button, QLabel("История последних партий:"), self.history_list, QLabel("Журнал событий:"), self.event_log):
            left_layout.addWidget(widget)
        right = QWidget(); right_layout = QVBoxLayout(right)
        for widget in (self.best_label, self.threshold, forecast_button, QLabel("ТОП-5 рекомендаций:"), self.recommendation_list, self.weights_label, self.stats_label, self.bank_label, self.canvas):
            right_layout.addWidget(widget)
        splitter.addWidget(left); splitter.addWidget(right)
        self.setCentralWidget(splitter)

    def start_parser(self) -> None:
        """Start automatic Selenium DOM polling from the GUI."""
        self.controller.engine.signal_threshold = self.threshold.value()
        self.controller.start(headless=self.headless_box.isChecked(), keep_alive_enabled=self.keep_alive_box.isChecked())
        self.parser_label.setText("Статус парсера: запуск")
        self.keep_alive_label.setText(f"KeepAlive: {'включён' if self.keep_alive_box.isChecked() else 'отключён'}")

    def stop_parser(self) -> None:
        """Stop automatic Selenium polling."""
        self.controller.stop()
        self.parser_label.setText("Статус парсера: остановка")

    def manual_forecast(self) -> None:
        """Build and save a recommendation without starting Selenium."""
        self.controller.engine.signal_threshold = self.threshold.value()
        self.controller.build_recommendations(save=True)
        self.refresh()

    def add_event(self, message: str) -> None:
        """Collect controller events for display on the next GUI tick."""
        self.pending_events.append(message)

    def refresh(self) -> None:
        """Refresh dashboard widgets from SQLite history and current engine state."""
        for message in self.pending_events[-50:]:
            self.event_log.insertItem(0, message)
        self.pending_events.clear()
        games = self.storage.list_games(limit=100)
        self.games_label.setText(f"Количество партий: {len(self.storage.list_games())}")
        if games:
            last = games[-1]
            self.last_result_label.setText(f"Последний результат: {last.sequence} / {last.combination.value if last.combination else '—'}")
        self.history_list.clear()
        for game in reversed(games[-20:]):
            self.history_list.addItem(f"{game.sequence} — {game.combination.value if game.combination else '—'}")
        recommendations = self.controller.engine.recommend(games)
        self.recommendation_list.clear()
        for rec in recommendations:
            self.recommendation_list.addItem(f"#{rec.rank}: первый кубик {rec.option.first_die}, {rec.option.combination.value}, рейтинг {rec.rating:.1f}, сигнал {rec.signal_strength:.0f}%, EV {rec.expected_value:.2f}")
        if recommendations:
            best = recommendations[0]
            skip = self.controller.engine.skip_message(recommendations)
            text = skip or f"Лучшая рекомендация: кубик {best.option.first_die} / {best.option.combination.value} / сигнал {best.signal_strength:.0f}%"
            self.best_label.setText(text)
        weights = self.controller.adaptive_weights.weights
        self.weights_label.setText("Веса алгоритмов: " + ", ".join(f"{name}={value:.2f}" for name, value in weights.items()))
        stats = self.storage.prediction_stats()
        self.stats_label.setText(f"Прогнозы: {stats.total}, TOP-1 {stats.top1_rate:.1f}%, TOP-3 {stats.top3_rate:.1f}%, серия {stats.current_streak}/{stats.best_streak}")
        metrics = self.controller.virtual_tester.metrics()
        self.bank_label.setText(f"Виртуальный банк: {metrics.balance:.2f} | ROI: {metrics.roi:.2f}% | DD: {metrics.max_drawdown:.2f}")
        self._draw_charts(games)

    def _draw_charts(self, games: list[GameResult]) -> None:
        """Draw combination and die-value distributions with matplotlib."""
        self.figure.clear()
        combo_ax = self.figure.add_subplot(121)
        value_ax = self.figure.add_subplot(122)
        for ax in (combo_ax, value_ax):
            ax.set_facecolor("#111827")
            ax.tick_params(colors="#e5e7eb", labelrotation=30)
        combo_counts = Counter(game.combination.value if game.combination else "—" for game in games)
        value_counts = Counter(value for game in games for value in game.dice)
        combo_ax.bar(list(combo_counts), list(combo_counts.values()), color="#38bdf8")
        value_ax.bar([str(value) for value in range(1, 7)], [value_counts[value] for value in range(1, 7)], color="#22c55e")
        combo_ax.set_title("Комбинации", color="#e5e7eb")
        value_ax.set_title("Значения кубиков", color="#e5e7eb")
        self.figure.tight_layout()
        for text in ("Статус подключения: не подключено", "Статус парсера: ожидание", "KeepAlive: отключён", "Количество партий: 0", "Последний результат: —", "История последних партий:"):
            left_layout.addWidget(QLabel(text))
        left_layout.addWidget(self.left_log)
        right = QWidget(); right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.best_label)
        right_layout.addWidget(QLabel("ТОП-5 рекомендаций / веса / статистика / журнал:"))
        right_layout.addWidget(self.right_log)
        right_layout.addWidget(self.bank_label)
        right_layout.addWidget(self.canvas)
        splitter.addWidget(left); splitter.addWidget(right)
        self.setCentralWidget(splitter)

    def refresh(self) -> None:
        """Refresh dashboard widgets from SQLite history and current engine state."""
        games = self.storage.list_games(limit=100)
        recommendations = self.engine.recommend(games)
        self.right_log.clear()
        for rec in recommendations:
            self.right_log.addItem(f"#{rec.rank}: первый кубик {rec.option.first_die}, {rec.option.combination.value}, рейтинг {rec.rating:.1f}, сигнал {rec.signal_strength:.0f}%")
        if recommendations:
            best = recommendations[0]
            self.best_label.setText(f"Лучшая рекомендация: {best.option.first_die} / {best.option.combination.value} / сигнал {best.signal_strength:.0f}%")
        self._draw_charts(games)

    def _draw_charts(self, games) -> None:
        """Draw compact combination distribution chart with matplotlib."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#111827")
        counts = {}
        for game in games:
            counts[game.combination.value if game.combination else "—"] = counts.get(game.combination.value if game.combination else "—", 0) + 1
        ax.bar(list(counts), list(counts.values()), color="#38bdf8")
        ax.tick_params(colors="#e5e7eb", labelrotation=30)
        self.canvas.draw_idle()


def run_gui() -> int:
    """Start the PySide6 application."""
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
