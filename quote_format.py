"""Portable formatting controls shared by editor, renderer and quote transfers."""
ENUMS = {
    "start": {"auto", "left", "quantity", "description"},
    "wrap": {"auto", "start", "description"},
    "align": {"left", "center", "right"},
    "amount_align": {"top", "center", "bottom"},
}
NUMBERS = {"font_size": (8, 14), "space_before": (0, 36),
           "space_after": (0, 24), "line_spacing": (1, 1.5)}
FLAGS = {"bold", "underline", "keep_next", "keep_together", "page_break"}


def validate(value):
    if not isinstance(value, dict):
        raise ValueError("Formatting must be an object.")
    for key, setting in value.items():
        if key in ENUMS and isinstance(setting, str) and setting in ENUMS[key]:
            continue
        if key in NUMBERS and type(setting) in (int, float):
            low, high = NUMBERS[key]
            if low <= setting <= high:
                continue
        if key in FLAGS and isinstance(setting, bool):
            continue
        raise ValueError(f"Invalid formatting setting: {key}")
    return value
