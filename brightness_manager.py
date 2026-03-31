import threading
from pathlib import Path

_STATE_FILE = Path(__file__).parent / ".brightness_state"
_lock = threading.Lock()
_matrix_ref = None


def _load_state():
    try:
        parts = _STATE_FILE.read_text().strip().split(",")
        brightness = int(parts[0])
        off = len(parts) > 1 and parts[1] == "off"
        return brightness, off
    except Exception:
        return 100, False


def _save_state():
    try:
        _STATE_FILE.write_text(f"{_brightness},{'off' if _is_off else 'on'}")
    except Exception:
        pass


_brightness, _is_off = _load_state()


def register_matrix(matrix):
    global _matrix_ref
    with _lock:
        _matrix_ref = matrix
        if _matrix_ref:
            if _is_off:
                _matrix_ref.Clear()
            else:
                _matrix_ref.brightness = _brightness
    print(f'[brightness_manager] Matrix registered: {_matrix_ref is not None}')


def get_brightness():
    with _lock:
        return _brightness


def is_off():
    with _lock:
        return _is_off


def power_off():
    global _is_off
    with _lock:
        _is_off = True
        if _matrix_ref:
            _matrix_ref.Clear()
    _save_state()


def power_on(brightness):
    global _is_off
    with _lock:
        _is_off = False
        if _matrix_ref:
            _matrix_ref.brightness = brightness
    _save_state()


def set_brightness(value):
    global _brightness
    with _lock:
        _brightness = value
        if _matrix_ref and not _is_off:
            _matrix_ref.brightness = value
    _save_state()
    print(f'[brightness_manager] set_brightness({value})')
