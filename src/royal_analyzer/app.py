"""Application entry point and logging configuration."""
from __future__ import annotations

import logging

from .gui import run_gui


def configure_logging() -> None:
    """Configure file and console logging for diagnostics."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[logging.FileHandler("royal_analyzer.log", encoding="utf-8"), logging.StreamHandler()])


def main() -> int:
    """Launch Royal Analyzer Pro desktop GUI."""
    configure_logging()
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
