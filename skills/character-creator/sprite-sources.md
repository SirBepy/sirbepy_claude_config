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
