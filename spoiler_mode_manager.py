import threading
from pathlib import Path

_STATE_FILE = Path(__file__).parent / ".spoiler_mode_state"
_GLOBAL_KEY = "__global__"
_lock = threading.Lock()


def _load_state():
    try:
        state = {}
        for line in _STATE_FILE.read_text().splitlines():
            key, _, value = line.partition("=")
            if key:
                state[key] = value.strip() == "on"
        return state
    except Exception:
        return {}


def _save_state():
    try:
        lines = [f"{key}={'on' if value else 'off'}" for key, value in _state.items()]
        _STATE_FILE.write_text("\n".join(lines))
    except Exception:
        pass


_state = _load_state()


def is_spoiler_mode():
    with _lock:
        return _state.get(_GLOBAL_KEY, False)


def set_spoiler_mode(value: bool):
    with _lock:
        _state[_GLOBAL_KEY] = value
    _save_state()
    print(f'[spoiler_mode_manager] Spoiler mode {"ON" if value else "OFF"}')


def is_team_spoiler_mode(team: str):
    with _lock:
        return _state.get(team, False)


def set_team_spoiler_mode(team: str, value: bool):
    with _lock:
        _state[team] = value
    _save_state()
    print(f'[spoiler_mode_manager] Spoiler mode for {team} {"ON" if value else "OFF"}')


def is_spoiler_free_for_team(team: str):
    """True if the global switch or that team's own switch is on."""
    with _lock:
        return _state.get(_GLOBAL_KEY, False) or _state.get(team, False)
