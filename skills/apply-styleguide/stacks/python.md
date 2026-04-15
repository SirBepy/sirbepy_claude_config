# apply-styleguide - python stack (pywebview)

Assumes `common.md` is already loaded. This file only adds python-specific steps.

For Python desktop projects, the styleguide is consumed by rendering real HTML inside a pywebview window. No CSS var porting, no re-encoding tokens - the HTML pulls the exact same CDN file a web project would.

## 1. Dependencies

Add `pywebview>=5.0` to `requirements.txt` and to `pyproject.toml` `[project].dependencies`. On Windows pywebview pulls in `pythonnet`; check PyPI for the current Python version support and set `requires-python` accordingly. Do not copy a stale pin from another project - verify wheel availability at the time you run the skill.

## 2. File layout

Put HTML dialogs inside the package, under a `ui/` subfolder:

```
src/<pkg>/ui/__init__.py
src/<pkg>/ui/<dialog>.html
```

Register the folder as package data in `pyproject.toml`:

```toml
[tool.setuptools.package-data]
<pkg> = ["ui/*.html"]
```

## 3. HTML template

Each dialog HTML file must:

- Link the styleguide CDN in `<head>` before any other stylesheet (see common.md).
- Load Phosphor Icons via CDN.
- Use the standard component classes from common.md - never hand-rolled component styles.
- Use CSS vars from common.md for any custom CSS - never hardcoded hex/px for themeable values.
- Talk to Python via `window.pywebview.api.<method>()` and close itself by calling a `submit()` / `cancel()` API method (Python calls `window.destroy()`).
- Bind Escape to cancel and Enter to the primary action.

## 4. Python host

A dialog module looks like this:

```python
import webview
from pathlib import Path

class _Api:
    def __init__(self, result): self._result = result; self.window = None
    def submit(self, value):
        self._result["value"] = value
        self.window.destroy()

def open_dialog() -> str | None:
    result = {"value": None}
    api = _Api(result)
    html = str(Path(__file__).resolve().parent / "ui" / "dialog.html")
    api.window = webview.create_window("Title", html, js_api=api, width=560, height=420)
    webview.start()
    return result["value"]
```

Resource paths must handle PyInstaller: check `sys._MEIPASS` first, fall back to `Path(__file__).resolve().parent`.

## 5. Window icon

pywebview on Windows/EdgeChromium does NOT accept an `icon=` argument, so the taskbar defaults to the Python feather in dev runs. Fix it by setting the window icon manually after `shown`:

```python
import win32api, win32con, win32gui
hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
big = win32gui.LoadImage(0, ico, win32con.IMAGE_ICON, 32, 32, win32con.LR_LOADFROMFILE)
small = win32gui.LoadImage(0, ico, win32con.IMAGE_ICON, 16, 16, win32con.LR_LOADFROMFILE)
win32api.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, big)
win32api.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, small)
```

Hook via `window.events.shown` with a small timer delay (~100ms) to let Windows finish creating the HWND. In bundled exe builds the `--icon=` PyInstaller flag covers the taskbar icon, but setting WM_SETICON also makes dev runs look correct.

## 6. PyInstaller build

Add to the PyInstaller command:

```
--add-data "src/<pkg>/ui/<dialog>.html;ui"
--collect-all webview
```

`--collect-all webview` is non-optional - pywebview ships data files (JS runtime, HTML shims) that PyInstaller otherwise misses.

## 7. Confirm

Follow the "Finish" section in `common.md`. Additionally note:

- Dialogs migrated (tkinter/Qt -> pywebview)
- `requires-python` set (with reason, if constrained)
