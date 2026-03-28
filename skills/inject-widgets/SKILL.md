---
name: inject-widgets
description: Triggers on /inject-widgets only.
---

# /inject-widgets

> Inject the settings widget and animated background into index.html.

## Workflow

### Step 1 - Check if already injected

Read `index.html`. If both script tags below already exist, tell the user and stop.

### Step 2 - Inject settings widget

Add the following just before `</body>` if not already present:

```html
<!-- Settings widget - comment out to disable -->
<script src="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/widget/settings.js"></script>
```

The widget always renders in the top-right corner.

Then check if there is any existing page-specific element with `position: fixed` or `position: absolute` in the top-right corner (e.g. a custom menu, a button, a panel). If there is, do not move the widget - instead adjust the page-specific element to sit below the widget. A safe offset is `top: 60px` or similar depending on the widget size.

### Step 3 - Inject animated background

Add the following just after the settings widget script, before `</body>`, if not already present:

```html
<!-- Animated background. To disable: set window.BEPY_BACKGROUND = false before this tag. To use a custom SVG: set window.BEPY_BG_PATTERN = 'your-pattern.svg' before this tag. -->
<script src="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@main/widget/background.js"></script>
```

### Step 4 - Confirm

Tell the user what was injected and flag any offset adjustments made to existing elements.
Do not commit - the user handles that.
