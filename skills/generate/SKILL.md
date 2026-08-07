---
name: generate
description: Generates images with free AI models via a provider cascade - Cloudflare Workers AI FLUX-1-schnell (~10k neurons/day free, the default), Gemini "nano banana" (needs billing; no free image tier), Pollinations as a keyless last resort. Use for raster references, logo/mascot concepts, hero images, placeholders, or whenever SVG hand-authoring can't reach the needed style (hands, faces, organic or painterly looks). Triggers - /generate, "generate an image", "AI image", "make a picture of".
argument-hint: "<what to generate>"
---

# /generate

> Free AI image generation from the CLI. One script, three providers, best-available first.

## The one command

```powershell
node "$env:USERPROFILE\.claude\skills\generate\generate.mjs" --prompt "<prompt>" --out ".for_bepy\generated\<slug>.png" --aspect 1:1 --n 4
```

It picks the best provider whose env vars are set, falls through to the next on any failure, verifies
the bytes are a real image, and prints a JSON summary of what was written. With `--n > 1` each file
gets a `-<seed>` suffix.

| Flag | Meaning |
|---|---|
| `--prompt` | Required. The full prompt (see framework below). |
| `--out` | Required. Target path; parent dirs are created. |
| `--aspect` | `1:1` (default), `4:3`, `3:4`, `16:9`, `9:16`, `3:2`, `2:3`. |
| `--n` | Variant count (default 1). Seeds auto-spread unless `--seed` is given. |
| `--seed` | First seed; `--n` counts up from it. Reproduces an exact image on Cloudflare/Pollinations. |
| `--provider` | Force `gemini` / `cloudflare` / `pollinations`, skipping the cascade. |
| `--model` | Override the Gemini model id. |
| `--steps` | Cloudflare FLUX steps, capped at 8 (default 8). |
| `--list-models` | Print the Gemini image models this key can see, plus the auto-pick. |
| `--allow-paid` | Required before any paid-tier model is used. See the billing gate below. |

## Provider cascade (measured 2026-08-07)

**1. Cloudflare Workers AI FLUX-1-schnell** - `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`.

**The default, and the only provider here that is actually free and actually good.** 10,000
neurons/day free, resetting 00:00 UTC (~2,000 small images), shared across all Workers AI models.
Sharp flat-vector and icon work, clean silhouettes, fast (~3s). A 1-8 step model, so it is weaker on
photoreal faces and busy scenes than a full diffusion model.

```
POST https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai/run/@cf/black-forest-labs/flux-1-schnell
     Authorization: Bearer $CLOUDFLARE_API_TOKEN
     {"prompt":"...", "steps":8, "seed":1000}     steps max 8, prompt max 2048 chars
  -> result.image                                  (base64 JPEG)
```

**2. Gemini "nano banana"** - `GEMINI_API_KEY`, key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

**There is no free tier for image generation, whatever the blog posts say.** Measured on a fresh key
2026-08-07: `gemini-flash-latest` TEXT returns 200, while every image model
(`gemini-2.5-flash-image`, `gemini-3.1-flash-image`, `gemini-3-pro-image`, all `imagen-4.0-*`)
returns 429 `generate_content_free_tier_requests, limit: 0`. Text is free, images are not. Do not
re-test this hoping for a different answer - it needs billing enabled on the Cloud project, which is
a `[BILLING]` question for Joe first. The widely-repeated "500 images/day free" figure did not hold.

```
POST https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent
     x-goog-api-key: $GEMINI_API_KEY
     {"contents":[{"role":"user","parts":[{"text":"..."}]}],
      "generationConfig":{"responseModalities":["TEXT","IMAGE"],"imageConfig":{"aspectRatio":"1:1"}}}
  -> candidates[0].content.parts[].inlineData.data   (base64 PNG)
```

The script discovers model ids from `GET /v1beta/models` (they move often) and skips paid markers.
Quotas are per Google Cloud **project**, not per key - extra keys in one project share a pool. There
is no seed parameter, so `--n` batches vary via a per-seed nonce appended to the prompt.

**3. Pollinations** - keyless, optional `POLLINATIONS_API_KEY`. Last resort only.

The catalog is `["sana"]` and has stayed that way: a small model whose output is soft abstract mush,
usable for rough silhouette references and nothing finished. Unknown `model=` values are **silently
substituted**, not rejected, so trust the `x-model-used` response header over what you asked for. The
account key Joe minted returns `x-auth-status: unauthenticated` and does not unlock FLUX - assume
that stays true unless their APIDOCS says otherwise. Anonymous rate limit ~1 request/15s.

**Not wired: Hugging Face Inference Providers.** The free tier is $0.10/month of credit, a handful of
images. Not worth the token plumbing; revisit only if that number changes.

## Billing gate - non-negotiable

Only genuinely free tiers run by default. The script refuses paid-tier Gemini models
(`gemini-3-pro-image` / nano banana Pro is **0 RPM, 0 RPD** on free; `imagen`, `ultra`) unless
`--allow-paid` is passed. Never pass it without asking Joe a `[BILLING]` question first. Same for
OpenAI GPT Image - metered from the first call, so it is not in the cascade at all.

## Prompt framework

Narrative direction, not keyword soup, in this order:

1. **Image type** - "A flat vector-style app icon", "A photorealistic photograph", "An isometric illustration"
2. **Subject** - who/what with concrete details
3. **Environment/background** - setting, or an exact solid color ("on a solid dark navy #1a1a2e background")
4. **Technical specs** - lighting, lens, style anchors ("clean geometric shapes, uniform stroke weight, high contrast")
5. **Constraints** - always end with "no text, no watermark, no border"

Same prompt + different seeds = cheap variant exploration. Different prompts per creative direction =
real variety. For icon work bake the target background color in - every provider here outputs opaque
raster, so there is no real transparency to ask for.

## Process

1. Build the prompt with the framework above.
2. Run the script into the project's scratch convention (`.for_bepy/generated/` where it exists, else `generated/`).
3. **Verify before showing, always.** The script already rejects non-images and sub-5KB responses, but
   that only proves a file arrived - Read the PNG back to confirm it actually matches the ask.
4. Show the result inline (Read) and give the full absolute path.
5. Iterate: tweak prompt or reroll seed. When a variant wins, record its exact prompt + seed + provider
   so it can be regenerated at other sizes.
6. Report the provider that actually served each image. A silent fall-through to Pollinations is the
   difference between a usable reference and mush, so never let it pass unmentioned.

## Scope notes

- Output is raster. For logo pipelines these are references or trace targets; final delivery still
  wants SVG (see the `create-logo` skill).
- Licensing: Gemini and Cloudflare outputs follow their respective terms and are fine for personal
  work; anything shipped commercially deserves a fresh check.
