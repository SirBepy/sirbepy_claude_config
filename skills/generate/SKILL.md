---
name: generate
description: Generates images with free AI models (Pollinations.ai, FLUX) via plain curl - no API key, no signup. Use for raster references, logo/mascot concepts, hero images, placeholders, or whenever SVG hand-authoring can't reach the needed style (hands, faces, organic or painterly looks). Triggers - /generate, "generate an image", "AI image", "make a picture of".
argument-hint: "<what to generate>"
---

# /generate

> Free AI image generation from the CLI. Pollinations.ai, keyless, curl in, PNG out.

## Primary API: Pollinations.ai (no key, no signup)

```powershell
curl.exe -sL "https://image.pollinations.ai/prompt/<URL-ENCODED-PROMPT>?model=flux&width=1024&height=1024&seed=42&nologo=true" -o out.png
```

- URL-encode the prompt first: `[uri]::EscapeDataString($prompt)` in PowerShell, or `node -e "console.log(encodeURIComponent(...))"`.
- **Params:** `model` (check `GET https://image.pollinations.ai/models` FIRST - unknown names are silently substituted, not rejected), `width`/`height` (up to ~2048), `seed` (same prompt+seed reproduces the image; vary seed for variants), `nologo=true`, `enhance=true` (server-side LLM prompt expansion - skip it when the prompt is already precise), `private=true` (keeps it off their public feed).
- **Quality reality check (measured 2026-08-07):** the anonymous catalog exposed ONLY `sana` - a small fast model whose output is soft and low-detail, fine for rough references, not for finished art. FLUX-class models need the free registered key. If quality matters and no key is set, say so instead of burning seeds hoping for better.
- **Rate limit:** anonymous tier is ~1 request per 15s. Space batch requests 15s apart and keep batches small (2-4 variants). A free key from enter.pollinations.ai raises limits and truly removes the watermark - if `POLLINATIONS_API_KEY` is set, send it as `Authorization: Bearer` and ignore the spacing.
- **Caveats:** best-effort service, no SLA; anonymous outputs may carry a small corner watermark; raster RGB only - no real transparency, so for icon work request a solid known background color and remove/trace it afterwards.

## Prompt framework (adapted from the 5-part pattern)

Build prompts as narrative direction, not keyword soup, in this order:

1. **Image type** - "A flat vector-style app icon", "A photorealistic photograph", "An isometric illustration"
2. **Subject** - who/what with concrete details
3. **Environment/background** - setting, or an exact solid color ("on a solid dark navy #1a1a2e background")
4. **Technical specs** - lighting, lens, style anchors ("clean geometric shapes, uniform stroke weight, high contrast")
5. **Constraints** - always end with "no text, no watermark, no border"

Same prompt + different seeds = cheap variant exploration. Different prompts per creative direction = real variety.

## Process

1. Build the prompt (framework above). For icon/logo use, bake the target background color in.
2. Pick size: 1024x1024 default; match the destination's aspect otherwise.
3. Download with curl to the project's scratch convention (`.for_bepy/generated/` where that exists, else `generated/`), filename `<slug>-<seed>.png`.
4. **Verify before showing, always:** the file must be a real image of plausible size (an error page is small text/HTML - check with `Get-Item` length, a real PNG is 50KB+), then Read the PNG back to confirm it matches the ask. Rate-limited (429) or 5xx: wait 15s, retry once, then report honestly.
5. Show the result inline (Read) and give the file path.
6. Iterate: tweak prompt or reroll seed. When a variant wins, note its exact prompt+seed so it can be regenerated at other sizes reproducibly.

## Keyed fallbacks (only if the user provides keys - never sign up on their behalf)

- **Cloudflare Workers AI** FLUX-1-schnell: `POST https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/run/@cf/black-forest-labs/flux-1-schnell` with `Authorization: Bearer $CF_API_TOKEN`, JSON `{"prompt": "..."}`. Free tier ~10k neurons/day.
- **Hugging Face / Together / Gemini / OpenAI**: all need accounts and have costs or metered tiers. Before using ANY keyed provider, surface it as a [BILLING] question first - Pollinations stays the default precisely because it is free.

## Scope notes

- Output is raster. For logo pipelines, treat generations as references or trace targets; final logo delivery still wants SVG (see the `create-logo` skill).
- Generated-image licensing on Pollinations is permissive (open-source platform), fine for personal projects; anything shipped commercially deserves a fresh check.
