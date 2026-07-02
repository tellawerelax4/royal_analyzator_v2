# Royal Analyzer Pro

Desktop and headless Python analyzer for the Royal game at `https://app.playnautica.ru/royal/`.

## Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Run desktop GUI

```bash
royal-analyzer gui
```

In the GUI press **Старт автоматического парсинга**. Enable **Headless Selenium** if you do not need to see the browser. The left panel shows connection/parser/KeepAlive status, history and logs. The right panel shows TOP-5 recommendations, signal threshold, adaptive weights, prediction stats, virtual bank and charts.

## Run automatic collection without GUI

```bash
royal-analyzer collect
```

Use a visible browser instead of headless mode:

```bash
royal-analyzer collect --headed --keep-alive
```

## Selectors

All website selectors are in `selectors.json`. If the site layout changes, update that file first. The parser only reads DOM nodes; OCR, screenshots and image analysis are not used.

## Diagnostics

When required DOM elements cannot be found, the app writes:

- `debug_page.html`
- `debug_stacktrace.log`
- `royal_analyzer.log`

If Chrome cannot start on Linux, install the system browser libraries required by Selenium/Chrome (for example `libatk`, `libnss3`, `libxkbcommon`, `libGL`) or run on a desktop system with Chrome/Chromium installed.
