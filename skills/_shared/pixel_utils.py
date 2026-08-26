"""Shared pixel-sampling helpers for design_diff.py and figma_pixel_diff.py:
box-average sampling over a numpy RGB array, plus hex formatting.

Numpy-slice semantics apply at every radius including 0, so negative and
out-of-bounds coordinates differ from PIL getpixel() and are untested here.
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
