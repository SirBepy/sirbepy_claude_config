# Sprite sources

Curated list for `/character-creator`. Try each in order until one returns a usable icon.

1. **The Spriters Resource** — https://www.spriters-resource.com  
   Search by character name. Each entry has direct PNG downloads of sprites and portraits. Best fit for 8/16/32-bit game characters. Search URL pattern: `https://www.spriters-resource.com/?s=<name>`.

2. **Sprite Database** — https://spritedatabase.net  
   Searchable archive organized by series and character. Useful when Spriters Resource has no entry.

3. **Wikipedia article infobox image**  
   The article's main image is often a clean square crop at 200x200 or larger. Use as a last resort. Licensing varies — check the file's license page on Commons before using in any shared bundle.

## What to skip

- Image generation models (out of scope for v1, per spec).
- Random Google Images results (legal grab-bag, quality grab-bag).
- DeviantArt fan art (often watermarked or inconsistent style).

## Cropping notes

- Target 64x64. Pixel-art sprites that are smaller (e.g. 32x32) should be upscaled with nearest-neighbor (no smoothing) so they stay crisp.
- Centered portrait crop. Avoid full-body silhouettes; the icon is shown at 22x22 and 48x48 so the face/torso is the priority.
- ImageMagick: `magick input.png -resize 64x64 -background transparent -gravity center -extent 64x64 icon.png`
- macOS: `sips -z 64 64 input.png --out icon.png` (lossy resampling; prefer ImageMagick when available).
