"""Shared pixel-sampling helpers for design_diff.py and figma_pixel_diff.py:
box-average sampling over a numpy RGB array, plus hex formatting. Extracted
2026-08-25 (todo 401) from near-identical copies that differed only in input
shape (in-memory array vs PNG path) and a getpixel() shortcut at radius 0.

Matches design_diff's original numpy-slice semantics uniformly at every
radius, including 0. That shortcut used PIL's getpixel(), which wraps
negative coordinates Python-list style and raises IndexError out of bounds -
genuinely different edge-case behaviour with no test coverage on either
side; see todo 401's report for the measured before/after diff. Every
in-bounds caller (the entire real usage of both scripts) is unaffected.
"""


def hex_from_rgb(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(int(round(c)) for c in rgb))


def sample_box(arr, x, y, radius=0):
    """Average an RGB numpy array over a (2*radius+1) square centered at
    (x, y), rounded to int per channel. Caller loads the array (RGB, any
    numeric dtype) and applies any coordinate scaling before calling."""
    box = arr[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1]
    mean = box.reshape(-1, 3).mean(axis=0)
    return tuple(int(round(c)) for c in mean)
