import threading
from pathlib import Path

_STATE_FILE = Path(__file__).parent / ".spoiler_mode_state"
_lock = threading.Lock()


def _load_state():
    try:
        return _STATE_FILE.read_text().strip() == "on"
    except Exception:
        return False


def _save_state():
    try:
        _STATE_FILE.write_text("on" if _spoiler_mode else "off")
    except Exception:
        pass


_spoiler_mode = _load_state()


def is_spoiler_mode():
    with _lock:
        return _spoiler_mode


def set_spoiler_mode(value: bool):
    global _spoiler_mode
    with _lock:
        _spoiler_mode = value
    _save_state()
    print(f'[spoiler_mode_manager] Spoiler mode {"ON" if value else "OFF"}')
