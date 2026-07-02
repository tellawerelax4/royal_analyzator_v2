"""Safe Selenium keep-alive actions that never place bets."""
from __future__ import annotations

import random
import threading
import time
from typing import Any

from selenium.webdriver.common.action_chains import ActionChains


class KeepAlive:
    """Move the mouse at random safe intervals to keep the broadcast active."""

    def __init__(self, driver: Any, enabled: bool = True, min_interval: int = 40, max_interval: int = 90) -> None:
        self.driver = driver
        self.enabled = enabled
        self.min_interval = min_interval
        self.max_interval = max_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start background keep-alive loop."""
        if not self.enabled or self._thread:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        """Perform random harmless pointer movements until stopped."""
        while not self._stop.wait(random.randint(self.min_interval, self.max_interval)):
            ActionChains(self.driver).move_by_offset(random.randint(-5, 5), random.randint(-5, 5)).perform()

    def stop(self) -> None:
        """Stop keep-alive loop."""
        self._stop.set()
