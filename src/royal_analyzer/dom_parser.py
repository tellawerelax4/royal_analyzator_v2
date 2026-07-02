"""Selenium DOM parser for Royal history; no OCR or screenshots are used."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement
from typing import Any

from selenium.webdriver.remote.webelement import WebElement

from .dice_decoder import decode_die, parse_grid_area
from .models import GameResult
from .statistics import classify_combination

LOGGER = logging.getLogger(__name__)


class DomParser:
    """Parse completed parties directly from HTML die nodes."""

    def __init__(self, selectors_path: str | Path = "selectors.json") -> None:
        self.selectors_path = Path(selectors_path)
        self.selectors: dict[str, Any] = json.loads(self.selectors_path.read_text(encoding="utf-8"))

    def decode_die_element(self, element: "WebElement") -> int:
    def decode_die_element(self, element: WebElement) -> int:
        """Decode one Selenium die element by reading child pip grid-area styles."""
        coords = []
        for pip in element.find_elements("css selector", self.selectors["pip"]):
            coord = parse_grid_area(pip.get_attribute("style") or "")
            if coord:
                coords.append(coord)
        return decode_die(coords)

    def parse_round(self, round_element: "WebElement") -> GameResult | None:
    def parse_round(self, round_element: WebElement) -> GameResult | None:
        """Parse a history row and return a completed five-dice result when available."""
        dice_elements = round_element.find_elements("css selector", self.selectors["die_container"])
        if len(dice_elements) < 5:
            return None
        dice = tuple(self.decode_die_element(element) for element in dice_elements[:5])
        if len(dice) != 5:
            return None
        result = GameResult(dice)  # type: ignore[arg-type]
        return GameResult(result.dice, result.timestamp, classify_combination(result.dice))

    def discover_rounds(self, driver: Any) -> list["WebElement"]:
        """Find likely completed party containers using selectors and a DOM fallback scan."""
        configured = driver.find_elements("css selector", self.selectors["round_container"])
        useful = [row for row in configured if len(row.find_elements("css selector", self.selectors["die_container"])) >= 5]
        if useful:
            return useful
        dice_elements = driver.find_elements("css selector", self.selectors["die_container"])
        rounds: list[WebElement] = []
        seen: set[str] = set()
        for die in dice_elements:
            ancestors = die.find_elements("xpath", "ancestor::*[.//*[@color='Red' or @color='Blue']]")
            for ancestor in ancestors:
                count = len(ancestor.find_elements("css selector", self.selectors["die_container"]))
                if count >= 5:
                    marker = ancestor.get_attribute("outerHTML")[:200]
                    if marker not in seen:
                        seen.add(marker)
                        rounds.append(ancestor)
                    break
        return rounds

    def parse_history(self, driver: Any) -> list[GameResult]:
        """Parse every completed game currently present in the page history."""
        rounds = self.discover_rounds(driver)
        result = GameResult(dice)  # type: ignore[arg-type]
        return GameResult(result.dice, result.timestamp, classify_combination(result.dice))

    def parse_history(self, driver: Any) -> list[GameResult]:
        """Parse every completed game currently present in the page history."""
        rounds = driver.find_elements("css selector", self.selectors["round_container"])
        results: list[GameResult] = []
        for row in rounds:
            try:
                result = self.parse_round(row)
                if result:
                    results.append(result)
            except Exception:
                LOGGER.exception("Failed to parse a Royal history row")
        return results
