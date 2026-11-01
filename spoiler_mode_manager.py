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

LOGGER = logging.getLogger("mlbled")

DEFAULT_SPOILER_FILE = "/var/lib/led-panel/spoiler"
FALLBACK_SPOILER_FILE = Path(__file__).parent / ".spoiler_mode_state"
POLL_INTERVAL = 1.0
_GLOBAL_KEY = "__global__"

_lock = threading.RLock()
_clock = time.monotonic  # replaced in tests
_state = {}
_last_poll = None
_last_problem = None


def reset() -> None:
    """Forget cached state (for tests)."""
    global _state, _last_poll, _last_problem
    with _lock:
        _state, _last_poll, _last_problem = {}, None, None


def spoiler_paths() -> list:
    return [Path(os.environ.get("MLB_PANEL_SPOILER") or DEFAULT_SPOILER_FILE), Path(FALLBACK_SPOILER_FILE)]


def _parse(text: str) -> dict:
    state = {}
    for line in text.splitlines():
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            state[key] = value.strip().lower() == "on"
    return state


def _problem(message: str) -> None:
    global _last_problem
    if message != _last_problem:
        LOGGER.warning("%s", message)
        _last_problem = message


def _read() -> dict:
    global _last_problem
    for path in spoiler_paths():
        try:
            text = path.read_bytes().decode("utf-8-sig", errors="replace")
        except FileNotFoundError:
            continue
        except OSError as e:
            _problem(f"Cannot read spoiler file {path}: {e}; keeping the last state")
            return _state
        _last_problem = None
        return _parse(text)
    return _state  # no file anywhere: nothing has been set, or keep what we had


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
        return _state.get(_GLOBAL_KEY, False)


def is_team_spoiler_mode(team: str) -> bool:
    with _lock:
        _refresh()
        return _state.get(team, False)


def is_spoiler_free_for_team(team: str) -> bool:
    """True if the global switch or that team's own switch is on."""
    with _lock:
        _refresh()
        return _state.get(_GLOBAL_KEY, False) or _state.get(team, False)
