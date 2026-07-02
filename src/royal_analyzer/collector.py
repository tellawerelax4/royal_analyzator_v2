"""Selenium collector that polls Royal history every 500 ms."""
from __future__ import annotations

import json
import logging
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any


from .dom_parser import DomParser
from .models import GameResult

LOGGER = logging.getLogger(__name__)


class SeleniumCollector:
    """Open the Royal page, poll DOM history, and emit newly completed parties."""

    def __init__(self, selectors_path: str | Path = "selectors.json", poll_interval: float = 0.5, headless: bool = False) -> None:
        self.selectors_path = Path(selectors_path)
        self.selectors = json.loads(self.selectors_path.read_text(encoding="utf-8"))
        self.poll_interval = poll_interval
        self.headless = headless
        self.parser = DomParser(selectors_path)
        self.driver: Any | None = None
        self.seen: set[str] = set()

    def start_driver(self) -> Any:
        """Create Selenium Chrome driver and navigate to the configured game URL."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.selectors["game_url"])
        return self.driver

    def analyze_structure(self) -> None:
        """Validate configured selectors on first launch and persist HTML on failure."""
        if not self.driver:
            raise RuntimeError("Driver is not started")
        try:
            self.driver.find_elements("css selector", self.selectors["round_container"])
        except Exception as exc:
            Path("debug_page.html").write_text(self.driver.page_source, encoding="utf-8")
            Path("debug_stacktrace.log").write_text("".join(traceback.format_exception(exc)), encoding="utf-8")
            raise

    def poll_once(self) -> list[GameResult]:
        """Read history once and return only results not seen before."""
        if not self.driver:
            raise RuntimeError("Driver is not started")
        parsed = self.parser.parse_history(self.driver)
        new_results: list[GameResult] = []
        for result in parsed:
            key = result.sequence
            if key not in self.seen:
                self.seen.add(key)
                new_results.append(result)
        return new_results

    def run(self, callback: Callable[[GameResult], None], stop: Callable[[], bool]) -> None:
        """Continuously poll until `stop` returns True."""
        self.start_driver()
        self.analyze_structure()
        while not stop():
            for result in self.poll_once():
                callback(result)
            time.sleep(self.poll_interval)

    def close(self) -> None:
        """Close the browser if it is running."""
        if self.driver:
            self.driver.quit()
            self.driver = None
