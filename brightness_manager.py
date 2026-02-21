import sys
_brightness = 100
_matrix_ref = None

def register_matrix(matrix):
    global _matrix_ref
    _matrix_ref = matrix
    print(f"[brightness_manager] Matrix registered: {_matrix_ref is not None}")

def set_brightness(value):
    global _brightness
    print(f"[brightness_manager] set_brightness({value})")
    if _matrix_ref:
        _matrix_ref.brightness = value

