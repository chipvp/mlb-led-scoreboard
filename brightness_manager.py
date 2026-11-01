"""Reader side of the shared LED panel brightness/power state.

The separate led-panel-control service (~/projects/led-panel-control) owns the HomeKit bridge and writes a one-line
state file, `<brightness>,<on|off>` (e.g. `40,on`, `40,off`). This module only READS it and applies it to the
registered matrix; it never writes the file.

State file, in order, on every poll:
  1. $MLB_PANEL_STATE, or /var/lib/led-panel/state when unset;
  2. the old local `.brightness_state` next to this file, used ONLY when the shared file cannot be opened
     (missing, or any other OSError). A shared file that exists but holds garbage does not fall through.

When the content is garbage, empty or half-written, or no file is readable, the LAST GOOD state keeps applying, so a
transient bad read never flashes a panel that is meant to be off. Only before any good read is the default used
(brightness 100, on). Each distinct problem is logged once. A leading UTF-8 BOM is ignored. Brightness is clamped to
1..100 (use `off` to blank the panel; `off` keeps the brightness).

`is_off()` / `get_brightness()` poll the file at most about once a second (the render loop calls `is_off()` every
frame), so no thread is needed.
"""

import logging
import os
import threading
import time
from pathlib import Path

LOGGER = logging.getLogger("mlbled")

DEFAULT_STATE_FILE = "/var/lib/led-panel/state"
FALLBACK_STATE_FILE = Path(__file__).parent / ".brightness_state"
POLL_INTERVAL = 1.0
MIN_BRIGHTNESS = 1
MAX_BRIGHTNESS = 100
DEFAULT_STATE = (MAX_BRIGHTNESS, False)  # (brightness, is_off)

_lock = threading.RLock()
_clock = time.monotonic  # replaced in tests
_matrix = None
_state = DEFAULT_STATE
_last_good = None  # last state read successfully; None until the first good read
_last_poll = None  # clock value of the last poll; None forces the next one
_applied_brightness = None
_applied_off = False
_last_problem = None
_warned_unreadable = set()


def reset() -> None:
    """Forget the matrix and all state (for tests)."""
    global _matrix, _state, _last_good, _last_poll, _applied_brightness, _applied_off, _last_problem
    with _lock:
        _matrix, _state, _last_good, _last_poll = None, DEFAULT_STATE, None, None
        _applied_brightness, _applied_off, _last_problem = None, False, None
        _warned_unreadable.clear()


def state_paths() -> list:
    """Candidate state files in priority order."""
    return [Path(os.environ.get("MLB_PANEL_STATE") or DEFAULT_STATE_FILE), Path(FALLBACK_STATE_FILE)]


def _clamp(brightness) -> int:
    return max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, int(brightness)))


def _parse(text: str) -> tuple:
    """'<brightness>,<on|off>' -> (clamped brightness, is_off). Raises ValueError for anything else."""
    parts = [p.strip().lower() for p in text.strip().split(",")]
    if len(parts) != 2 or parts[1] not in ("on", "off"):
        raise ValueError(f"expected '<brightness>,<on|off>', got {text.strip()[:40]!r}")
    return _clamp(parts[0]), parts[1] == "off"


def _problem(message: str) -> None:
    """Log a failure the first time it occurs (and again only if it changes)."""
    global _last_problem
    if message != _last_problem:
        LOGGER.warning("%s", message)
        _last_problem = message


def _keep() -> tuple:
    return _last_good if _last_good is not None else DEFAULT_STATE


def _read() -> tuple:
    global _last_problem, _last_good
    for path in state_paths():
        try:
            text = path.read_bytes().decode("utf-8-sig", errors="replace")
        except FileNotFoundError:
            continue
        except OSError as e:  # present but unreadable: say so once, try the next path
            message = f"Cannot read panel state file {path}: {e}"
            if message not in _warned_unreadable:
                _warned_unreadable.add(message)
                LOGGER.warning("%s", message)
            continue
        try:
            state = _parse(text)
        except ValueError as e:
            state = _keep()
            _problem(f"Ignoring panel state file {path}: {e}; keeping {state[0]},{'off' if state[1] else 'on'}")
            return state
        _last_problem = None
        _last_good = state
        return state
    state = _keep()
    _problem(
        f"No usable panel state file ({', '.join(str(p) for p in state_paths())}); keeping {state[0]},{'off' if state[1] else 'on'}"
    )
    return state


def _apply() -> None:
    """Clear on entering off, set brightness only when it changed. Never raises."""
    global _applied_brightness, _applied_off
    if _matrix is None:
        return
    brightness, off = _state
    try:
        if off:
            if not _applied_off:
                _matrix.Clear()
        elif brightness != _applied_brightness:
            _matrix.brightness = brightness
            _applied_brightness = brightness
    except Exception:  # the panel control is a bonus; never stop the board
        LOGGER.exception("Failed to apply panel state to the matrix")
    _applied_off = off


def _poll(force: bool = False) -> None:
    global _state, _last_poll
    now = _clock()
    if not force and _last_poll is not None and 0 <= now - _last_poll < POLL_INTERVAL:
        return
    _last_poll = now
    _state = _read()
    _apply()


def poll_state() -> None:
    """Re-read the state file now (rate limiting is skipped) and apply it."""
    with _lock:
        _poll(force=True)


def register_matrix(matrix) -> None:
    """Remember the matrix and apply the current state to it right away."""
    global _matrix, _applied_brightness, _applied_off
    with _lock:
        _matrix, _applied_brightness, _applied_off = matrix, None, False
        _poll(force=True)
    print(f"[brightness_manager] Matrix registered: {matrix is not None}", flush=True)


def get_brightness() -> int:
    with _lock:
        _poll()
        return _state[0]


def is_off() -> bool:
    with _lock:
        _poll()
        return _state[1]
