"""Reader side of the shared spoiler switches.

The led-panel-control service (~/projects/led-panel-control) writes `/var/lib/led-panel/spoiler` (override with
$MLB_PANEL_SPOILER), lines of `key=on|off` where the key is a team name as in `Config.preferred_teams` or
`__global__`. This module only reads it, cached and re-read at most once a second. A read error keeps the last good
state. The old local `.spoiler_mode_state` is used ONLY when the shared file is missing.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger("mlbled")

DEFAULT_SPOILER_FILE = "/var/lib/led-panel/spoiler"
FALLBACK_SPOILER_FILE = Path(__file__).parent / ".spoiler_mode_state"
POLL_INTERVAL = 1.0
_GLOBAL_KEY = "__global__"

_lock = threading.RLock()
_clock = time.monotonic  # replaced in tests
_state: dict[str, bool] = {}
_last_poll: Optional[float] = None
_last_problem: Optional[str] = None
_shared_good = False


def reset() -> None:
    """Forget cached state (for tests)."""
    global _state, _last_poll, _last_problem, _shared_good
    with _lock:
        _state, _last_poll, _last_problem, _shared_good = {}, None, None, False


def spoiler_paths() -> list:
    return [Path(os.environ.get("MLB_PANEL_SPOILER") or DEFAULT_SPOILER_FILE), Path(FALLBACK_SPOILER_FILE)]


def _parse(text: str) -> dict:
    """Raises ValueError when no line is a valid `key=on|off` (empty or damaged file)."""
    state = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip().lower()
        if key and sep and value in ("on", "off"):
            state[key] = value == "on"
    if not state:
        raise ValueError("no valid 'key=on|off' line")
    return state


def _problem(message: str) -> None:
    global _last_problem
    if message != _last_problem:
        LOGGER.warning("%s", message)
        _last_problem = message


def _read() -> dict:
    """Shared file first; the legacy local file ONLY if the shared one is missing and no good shared read has
    happened. Any other failure, or an empty/damaged file, keeps the last good state."""
    global _last_problem, _shared_good
    shared, legacy = spoiler_paths()
    path, from_shared = shared, True
    try:
        text = shared.read_bytes().decode("utf-8-sig", errors="replace")
    except FileNotFoundError:
        if _shared_good:
            _problem(f"Spoiler file {shared} vanished; keeping the last state")
            return _state
        path, from_shared = legacy, False
        try:
            text = legacy.read_bytes().decode("utf-8-sig", errors="replace")
        except OSError as e:
            if not isinstance(e, FileNotFoundError):
                _problem(f"Cannot read spoiler file {legacy}: {e}; keeping the last state")
            return _state
    except OSError as e:
        _problem(f"Cannot read spoiler file {shared}: {e}; keeping the last state")
        return _state
    try:
        state = _parse(text)
    except ValueError as e:
        _problem(f"Ignoring spoiler file {path}: {e}; keeping the last state")
        return _state
    _last_problem = None
    if from_shared:
        _shared_good = True
    return state


def _refresh() -> None:
    global _state, _last_poll
    now = _clock()
    if _last_poll is not None and 0 <= now - _last_poll < POLL_INTERVAL:
        return
    _last_poll = now
    _state = _read()


def is_spoiler_mode() -> bool:
    with _lock:
        _refresh()
        return bool(_state.get(_GLOBAL_KEY, False))


def is_team_spoiler_mode(team: str) -> bool:
    with _lock:
        _refresh()
        return bool(_state.get(team, False))


def is_spoiler_free_for_team(team: str) -> bool:
    """True if the global switch or that team's own switch is on."""
    with _lock:
        _refresh()
        return bool(_state.get(_GLOBAL_KEY, False) or _state.get(team, False))
