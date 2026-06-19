# Sprite / icon sources

Curated list for `/character-creator`. Try in order. Skip dead ones immediately - don't waste turns.

## Sites that WORK

1. **Wikipedia article infobox image**
   Pattern: fetch `https://en.wikipedia.org/wiki/<Page>` via WebFetch, extract the `upload.wikimedia.org/...` URL of the infobox image, then `Invoke-WebRequest` to download. Often square, clean, and high-res enough to crop to 64x64.

2. **Game-specific fan wikis (Fandom, dedicated wikis)**
   Most have per-character pages with portrait images hosted on Fandom CDN (`static.wikia.nocookie.net/...`). WebFetch the page to get the image URL, then download.

3. **archive.org screenshot / sprite sheet items**
   Search archive.org for the game name. Some uploads include sprite sheets, manuals, or screenshots that contain usable portraits. Direct downloads work.

4. **Game manuals / box art via archive.org**
   Pattern: `archive.org/details/<game>-manual` often has scanned PDFs or PNGs with clean character art.

## Blizzard CASC (local install) - SQUARE in-game portraits, Blizzard-ONLY

OPT-IN fallback, not the default. Use this ONLY when you want a clean SQUARE
in-game hero portrait AND a local Blizzard install is present. Web sources above
stay the default. This is a Blizzard-CASC-only recipe: it works for CASC titles
(Heroes of the Storm, SC2, Diablo, Overwatch, WoW) and does NOT generalize to
non-CASC games (Sims, Army Men, Warcraft 3 / MPQ). Do not frame it as a
universal extractor.

Proven recipe (Heroes of the Storm, no CascLib rebuild and no sudo needed):

1. Extract the square portrait DDS via `storm-extract` (WSL build):
   ```bash
   storm-extract -i "<HotS install path>" -f heroselect_btn -t dds -x
   ```
   This yields `storm_ui_ingame_heroselect_btn_<codename>.dds` files.
2. Convert DDS -> PNG on Windows with python + Pillow (Pillow reads DDS):
   ```python
   from PIL import Image
   Image.open("storm_ui_ingame_heroselect_btn_<codename>.dds").save("portrait.png")
   ```
   Then crop/resize to 64x64 and flatten per the sections below.

Gotchas:
- **id -> codename**: the in-game asset uses Blizzard codenames, not display
  names. The id->codename alias map lives in memory `project_hots_character_sources`.
- **Tall-asset aspect check**: a few heroes' `heroselect_btn` is NOT square
  (chogall / barbarian are 75x201). For those, use the 76px `hero_icon` asset
  instead, or you'll get a stretched portrait. Always check aspect before resize.
- **Partial-install gaps**: abathur / qhira were missing from one local install;
  fall back to a web source for any codename `storm-extract` doesn't yield.

## Sites that BLOCK with 403 - skip immediately

- `spriters-resource.com`
- `sounds-resource.com`
- `myinstants.com`
- `101soundboards.com`
- `zapsplat.com`

Don't waste a turn fetching these. They will 403 deterministically.

## What to skip

- Image generation models (out of scope for v1).
- Random Google Images (legal grab-bag, quality grab-bag).
- DeviantArt fan art (watermarked / inconsistent).

## Cropping / resizing

ImageMagick is NOT installed. Use Python Pillow:

```python
from PIL import Image
img = Image.open("input.png")
# Pixel art: nearest-neighbor preserves crispness
out = img.resize((64, 64), Image.NEAREST)
# Photo / smooth art: LANCZOS
# out = img.resize((64, 64), Image.LANCZOS)
out.save("icon.png")
```

For sprite sheets, crop first then resize:

```python
img.crop((x1, y1, x2, y2)).resize((64, 64), Image.NEAREST).save("icon.png")
```

Target 64x64. The icon renders at 22x22 and 48x48 in the app, so face/torso must be the focal point - avoid full-body silhouettes.

## ALWAYS flatten transparency onto an opaque background

NEVER save an icon with a transparent (alpha) background. Many sources ship
non-rectangular cutouts — HotS draft portraits are hexagons on transparency, so
on a square/circular tile the corners show through and read as "a stupid
hexagram." The app fills behind them at render time, but the icons themselves
must still be opaque rectangles so they look right everywhere (sidebar strip,
chat-header circle, anywhere new).

Flatten as the LAST step, after resize. Fill with the art's own average colour
so any cutout corners blend instead of showing a hard frame:

```python
from PIL import Image

out = out.convert("RGBA")
# Average colour of the opaque pixels = a fill that blends with the art.
px = [p[:3] for p in out.getdata() if p[3] > 8]
avg = tuple(sum(c) // len(px) for c in zip(*px)) if px else (20, 22, 28)
bg = Image.new("RGB", out.size, avg)
bg.paste(out, mask=out.split()[3])   # composite using the alpha channel
bg.save("icon.png")                  # opaque RGB, no alpha
```

Verify: `Image.open("icon.png").mode` must be `"RGB"` (no `A`). If a source is
already a clean opaque rectangle, this step is a harmless no-op.
