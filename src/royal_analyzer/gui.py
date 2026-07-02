"""PySide6 dark desktop interface for Royal Analyzer Pro."""
from __future__ import annotations

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
