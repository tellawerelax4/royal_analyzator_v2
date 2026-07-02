"""Application entry point and logging configuration."""
from __future__ import annotations

import argparse
import logging
import signal
import time

from .controller import RoyalAnalyzerController
import logging

from .gui import run_gui


def configure_logging() -> None:
    """Configure file and console logging for diagnostics."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[logging.FileHandler("royal_analyzer.log", encoding="utf-8"), logging.StreamHandler()])


def run_collect(headless: bool = True, keep_alive: bool = False) -> int:
    """Run automatic DOM collection and analysis without the desktop GUI."""
    controller = RoyalAnalyzerController()
    controller.add_listener(lambda message: print(message, flush=True))
    controller.start(headless=headless, keep_alive_enabled=keep_alive)
    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True
        controller.stop()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    while not stop and controller.is_running():
        time.sleep(0.5)
    return 1 if controller.last_error else 0


def run_gui() -> int:
    """Import and start the PySide6 GUI lazily so CLI mode works without GUI libraries."""
    from .gui import run_gui as start_gui

    return start_gui()


def main() -> int:
    """Launch Royal Analyzer Pro in GUI or headless collection mode."""
    configure_logging()
    parser = argparse.ArgumentParser(description="Royal Analyzer Pro")
    parser.add_argument("mode", nargs="?", choices=("gui", "collect"), default="gui", help="gui: desktop interface, collect: headless parser/analyzer")
    parser.add_argument("--headed", action="store_true", help="Run Selenium with a visible browser in collect mode")
    parser.add_argument("--keep-alive", action="store_true", help="Enable safe mouse-move keep-alive in collect mode")
    args = parser.parse_args()
    if args.mode == "collect":
        return run_collect(headless=not args.headed, keep_alive=args.keep_alive)
def main() -> int:
    """Launch Royal Analyzer Pro desktop GUI."""
    configure_logging()
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
