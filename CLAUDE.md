# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run (hardware):**
```bash
sudo ./main.py
```

**Run (emulator, no hardware needed):**
```bash
./main.py --emulated
```

**Run with custom config:**
```bash
./main.py --config=custom_config  # omit .json extension
```

**Run tests:**
```bash
RGBME_SUPPRESS_ADAPTER_LOAD_ERRORS=1 python -m unittest
```

**Lint:**
```bash
flake8  # max line length 120, configured in .flake8
```

**Validate config:**
```bash
python validate_config.py
```

**Check version:**
```bash
python3 version.py
```

**Install (Raspberry Pi):**
```bash
sudo ./install.sh [--emulator-only] [--skip-matrix] [--skip-python] [--no-venv]
```

## Architecture

The project follows a **data-fetching + render loop** architecture with two main threads:

- **Main thread**: Manages data refresh loops (polling MLB StatsAPI every 0.5–30s depending on game state), determines which screen type to show, and rotates through games.
- **Render thread** (`MainRenderer` in `renderers/main.py`): Continuously draws to the LED matrix, delegating to screen-specific renderers.

### Data Flow

```
MLB StatsAPI → data/__init__.py (Data class) → renderers/main.py (MainRenderer) → LED matrix
```

The `Data` class (`data/__init__.py`) is the central orchestrator — it holds the schedule, current game, standings, weather, and headlines. The main loop calls `data.refresh_game()` and similar methods, then signals the render thread.

### Key Components

**`data/`** — All data fetching and state:
- `__init__.py`: `Data` class; orchestrates fetching and exposes state to renderers
- `game.py`: Game model (score, status, pitchers, at-bat info)
- `schedule.py`: Today's list of games
- `standings.py`: Division/wildcard standings
- `scoreboard/`: Intermediate models for pregame, live, and postgame screen content

**`renderers/`** — All display logic:
- `main.py`: `MainRenderer` — main render loop, picks which renderer to invoke
- `games/`: Renderers for live (`game.py`), pregame (`pregame.py`), and postgame (`postgame.py`) states
- `standings.py`, `offday.py`, `scrollingtext.py`, `network.py`: Other screen types

**`driver/`** — Hardware abstraction layer:
- Wraps `rgbmatrix` (real hardware) and `RGBMatrixEmulator` (software emulator)
- Falls back to emulator if hardware driver fails to load — this is how tests run

**`data/config/`** — Configuration management:
- Parses `config.json` (user creates from `config.example.json`)
- Manages layout positioning (from `coordinates/` JSON files) and color themes (from `colors/` JSON files)

**`homekit_server.py` / `brightness_manager.py`** — Recent HomeKit integration for controlling power/brightness via Apple Home.

### Screen Type Routing

`main.py` determines one of several `ScreenType` values and launches the corresponding refresh loop:
- `GAMEDAY`: Live games available; rotates through them
- `PREFERRED_TEAM_OFFDAY`: Preferred team has no game; optionally shows news/standings
- `LEAGUE_OFFDAY`: No MLB games today
- `ALWAYS_NEWS` / `ALWAYS_STANDINGS`: Config-forced modes

### Configuration

Copy `config.example.json` → `config.json`. Key settings:
- `preferred.teams`: Your team(s) — affects rotation priority and offday behavior
- `rotation.rates`: How long each game is shown (seconds) per status (live/pregame/final)
- `api_refresh_rate`: MLB API poll interval (minimum 3s)
- `demo_date`: Set to `"YYYY-MM-DD"` to replay a historical date
- `weather.apikey`: OpenWeatherMap API key for weather display
- Board dimensions come from CLI args (`--led-rows`, `--led-cols`), not config.json

### Coordinates & Colors

Layout positions for different board sizes live in `coordinates/` as JSON files (named by dimension, e.g., `w64h32.json`). Team colors live in `colors/`. Both are loaded at startup by the config system and can be customized without touching Python code.

### Tests

Tests live in `tests/` and cover game data, schedule, standings, config validation, fonts, colors, and data freshness. They run entirely in emulator mode — no hardware required. The env var `RGBME_SUPPRESS_ADAPTER_LOAD_ERRORS=1` suppresses expected warnings during test runs.
