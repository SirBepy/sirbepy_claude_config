#!/usr/bin/env node
// Free-tier image-gen cascade: Gemini (nano banana) -> Cloudflare FLUX-schnell -> Pollinations.
// Paid-tier models are never auto-selected; --model must name them explicitly.

import { writeFile } from 'node:fs/promises';
import { basename, dirname, join, extname } from 'node:path';
import { mkdirSync } from 'node:fs';

const GEMINI_HOST = 'https://generativelanguage.googleapis.com/v1beta';
const POLLI_HOST = 'https://image.pollinations.ai';

// Measured 2026-08-07: every Gemini image model returns free-tier limit:0 on a fresh key, so this
// order only matters once billing is enabled. 2.5 stays first as the one Google documents as free.
const GEMINI_FREE_PREFERENCE = [
  'gemini-2.5-flash-image',
  'gemini-3.1-flash-image',
  'gemini-2.0-flash-preview-image-generation',
];
const GEMINI_PAID_MARKERS = ['pro-image', 'imagen', 'ultra'];

const ASPECT_PX = {
  '1:1': [1024, 1024],
  '4:3': [1152, 896],
  '3:4': [896, 1152],
  '16:9': [1344, 768],
  '9:16': [768, 1344],
  '3:2': [1216, 832],
  '2:3': [832, 1216],
};

function parseArgs(argv) {
  const out = { n: 1, aspect: '1:1', provider: 'auto', steps: 8 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const key = a.slice(2);
    if (key === 'list-models' || key === 'allow-paid' || key === 'quiet') {
      out[key.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = true;
      continue;
    }
    out[key.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = argv[++i];
  }
  if (out.n) out.n = Number(out.n);
  if (out.seed !== undefined) out.seed = Number(out.seed);
  if (out.steps) out.steps = Number(out.steps);
  return out;
}

function die(msg) {
  console.error(`ERROR: ${msg}`);
  process.exit(1);
}

function sniff(buf) {
  if (buf.length > 8 && buf[0] === 0x89 && buf[1] === 0x50) return 'png';
  if (buf.length > 3 && buf[0] === 0xff && buf[1] === 0xd8) return 'jpg';
  return null;
}

function seedName(out, seed, ext) {
  const dir = dirname(out);
  const stem = basename(out, extname(out));
  return join(dir, `${stem}-${seed}.${ext}`);
}

async function geminiModels(key) {
  const res = await fetch(`${GEMINI_HOST}/models`, { headers: { 'x-goog-api-key': key } });
  if (!res.ok) throw new Error(`model list ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const body = await res.json();
  return (body.models || [])
    .map((m) => m.name.replace(/^models\//, ''))
    .filter((n) => /image/i.test(n));
}

function pickGeminiModel(available, allowPaid) {
  const usable = allowPaid
    ? available
    : available.filter((n) => !GEMINI_PAID_MARKERS.some((p) => n.includes(p)));
  for (const want of GEMINI_FREE_PREFERENCE) {
    const hit = usable.find((n) => n === want) || usable.find((n) => n.startsWith(want));
    if (hit) return hit;
  }
  return usable[0] || null;
}

async function geminiGenerate({ key, model, prompt, aspect, withImageConfig = true }) {
  const generationConfig = { responseModalities: ['TEXT', 'IMAGE'] };
  if (withImageConfig) generationConfig.imageConfig = { aspectRatio: aspect };

  const res = await fetch(`${GEMINI_HOST}/models/${model}:generateContent`, {
    method: 'POST',
    headers: { 'x-goog-api-key': key, 'content-type': 'application/json' },
    body: JSON.stringify({ contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig }),
  });

  if (!res.ok) {
    const text = await res.text();
    // Older image models reject imageConfig outright; retry once at their native square.
    if (res.status === 400 && withImageConfig && /imageConfig|aspect/i.test(text)) {
      return geminiGenerate({ key, model, prompt, aspect, withImageConfig: false });
    }
    throw new Error(`${res.status}: ${text.slice(0, 400)}`);
  }

  const body = await res.json();
  const parts = body?.candidates?.[0]?.content?.parts || [];
  const img = parts.find((p) => p.inlineData?.data);
  if (!img) {
    const said = parts.map((p) => p.text).filter(Boolean).join(' ').slice(0, 300);
    throw new Error(`no image in response${said ? ` (model said: ${said})` : ''}`);
  }
  return Buffer.from(img.inlineData.data, 'base64');
}

async function cloudflareGenerate({ token, account, prompt, seed, steps, withSeed = true }) {
  const url = `https://api.cloudflare.com/client/v4/accounts/${account}/ai/run/@cf/black-forest-labs/flux-1-schnell`;
  const sendSeed = withSeed && seed !== undefined;
  const res = await fetch(url, {
    method: 'POST',
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: JSON.stringify({ prompt, steps: Math.min(steps, 8), ...(sendSeed ? { seed } : {}) }),
  });
  if (!res.ok) {
    const text = await res.text();
    // Some backends behind this endpoint reject /seed as an unevaluated property; it is optional.
    if (res.status === 400 && sendSeed && /seed/.test(text)) {
      return cloudflareGenerate({ token, account, prompt, seed, steps, withSeed: false });
    }
    throw new Error(`${res.status}: ${text.slice(0, 400)}`);
  }

  const type = res.headers.get('content-type') || '';
  if (type.includes('application/json')) {
    const body = await res.json();
    if (!body.success && body.errors?.length) throw new Error(JSON.stringify(body.errors).slice(0, 400));
    const b64 = body?.result?.image;
    if (!b64) throw new Error('no result.image in response');
    return Buffer.from(b64, 'base64');
  }
  return Buffer.from(await res.arrayBuffer());
}

async function pollinationsGenerate({ prompt, seed, aspect, key }) {
  const [w, h] = ASPECT_PX[aspect] || ASPECT_PX['1:1'];
  const qs = new URLSearchParams({ width: String(w), height: String(h), nologo: 'true', private: 'true' });
  if (seed !== undefined) qs.set('seed', String(seed));
  const res = await fetch(`${POLLI_HOST}/prompt/${encodeURIComponent(prompt)}?${qs}`, {
    headers: key ? { authorization: `Bearer ${key}` } : {},
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
  return { buf: Buffer.from(await res.arrayBuffer()), model: res.headers.get('x-model-used') || 'unknown' };
}

function resolveProvider(requested) {
  const gem = process.env.GEMINI_API_KEY;
  const cfT = process.env.CLOUDFLARE_API_TOKEN;
  const cfA = process.env.CLOUDFLARE_ACCOUNT_ID;
  if (requested !== 'auto') return requested;
  if (cfT && cfA) return 'cloudflare';
  if (gem) return 'gemini';
  return 'pollinations';
}

const args = parseArgs(process.argv.slice(2));

if (args.listModels) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) die('GEMINI_API_KEY not set');
  const models = await geminiModels(key);
  console.log(JSON.stringify({ imageModels: models, autoPick: pickGeminiModel(models, false) }, null, 2));
  process.exit(0);
}

if (!args.prompt) die('--prompt is required');
if (!args.out) die('--out is required (path to the png/jpg to write)');
mkdirSync(dirname(args.out), { recursive: true });

const order = ['cloudflare', 'gemini', 'pollinations'];
const first = resolveProvider(args.provider);
const chain = args.provider === 'auto' ? order.slice(order.indexOf(first)) : [first];

const seeds = args.seed !== undefined
  ? Array.from({ length: args.n }, (_, i) => args.seed + i)
  : Array.from({ length: args.n }, (_, i) => 1000 + i * 137);

const written = [];
for (const seed of seeds) {
  let saved = false;
  for (const provider of chain) {
    try {
      let buf;
      let model = provider;

      if (provider === 'gemini') {
        const key = process.env.GEMINI_API_KEY;
        if (!key) throw new Error('GEMINI_API_KEY not set');
        model = args.model || pickGeminiModel(await geminiModels(key), !!args.allowPaid);
        if (!model) throw new Error('no free image model available on this key');
        if (!args.allowPaid && GEMINI_PAID_MARKERS.some((p) => model.includes(p))) {
          throw new Error(`${model} is a paid-tier model; pass --allow-paid to use it`);
        }
        // Gemini has no seed param, so variants come from a per-seed nonce in the prompt.
        const varied = seeds.length > 1 ? `${args.prompt}\n\n(Variation ${seed}: change composition and angle.)` : args.prompt;
        buf = await geminiGenerate({ key, model, prompt: varied, aspect: args.aspect });
      } else if (provider === 'cloudflare') {
        const token = process.env.CLOUDFLARE_API_TOKEN;
        const account = process.env.CLOUDFLARE_ACCOUNT_ID;
        if (!token || !account) throw new Error('CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID not set');
        model = 'flux-1-schnell';
        buf = await cloudflareGenerate({ token, account, prompt: args.prompt, seed, steps: args.steps });
      } else {
        const r = await pollinationsGenerate({ prompt: args.prompt, seed, aspect: args.aspect, key: process.env.POLLINATIONS_API_KEY });
        buf = r.buf;
        model = `pollinations/${r.model}`;
      }

      const ext = sniff(buf);
      if (!ext) throw new Error(`response was not an image (${buf.length} bytes)`);
      if (buf.length < 5000) throw new Error(`suspiciously small image (${buf.length} bytes)`);

      const path = seeds.length > 1 ? seedName(args.out, seed, ext) : args.out;
      await writeFile(path, buf);
      written.push({ provider, model, seed, path, bytes: buf.length });
      if (!args.quiet) console.log(`ok  ${provider} (${model})  seed=${seed}  ${buf.length} bytes  -> ${path}`);
      saved = true;
      break;
    } catch (err) {
      if (!args.quiet) console.error(`--  ${provider} failed: ${err.message}`);
    }
  }
  if (!saved) die(`all providers failed for seed ${seed}`);
}

console.log(JSON.stringify({ written }, null, 2));
