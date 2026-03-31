from pathlib import Path

_STATE_FILE = Path(__file__).parent / ".brightness_state"
_matrix_ref = None
_is_off = False


def _load_brightness():
    try:
        return int(_STATE_FILE.read_text().strip())
    except Exception:
        return 100


def _save_brightness(value):
    try:
        _STATE_FILE.write_text(str(value))
    except Exception:
        pass


_brightness = _load_brightness()


def register_matrix(matrix):
    global _matrix_ref
    _matrix_ref = matrix
    print(f'[brightness_manager] Matrix registered: {_matrix_ref is not None}')
    if _matrix_ref:
        _matrix_ref.brightness = _brightness


def get_brightness():
    return _brightness


def is_off():
    return _is_off


def power_off():
    global _is_off
    _is_off = True
    if _matrix_ref:
        _matrix_ref.Clear()


def power_on(brightness):
    global _is_off
    _is_off = False
    if _matrix_ref:
        _matrix_ref.brightness = brightness


def set_brightness(value):
    global _brightness
    _brightness = value
    _save_brightness(value)
    print(f'[brightness_manager] set_brightness({value})')
    if _matrix_ref and not _is_off:
        _matrix_ref.brightness = value
