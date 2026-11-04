// Turns recorded takes into one watchable clip with narration, and proves no two lines overlap by
// measuring the silence between them in the finished file.
const fs = require('fs');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const RATE = 24000;

// Reads the mono 16-bit PCM body of a WAV. tts.py writes exactly this shape.
function readPcm(file) {
  const b = fs.readFileSync(file);
  let at = 12;
  while (at < b.length) {
    const id = b.toString('ascii', at, at + 4);
    const size = b.readUInt32LE(at + 4);
    if (id === 'data') return b.subarray(at + 8, at + 8 + size);
    at += 8 + size + (size % 2);
  }
  throw new Error(`no data chunk in ${file}`);
}

function writeWav(file, pcm) {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + pcm.length, 4); h.write('WAVEfmt ', 8);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(RATE, 24); h.writeUInt32LE(RATE * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write('data', 36); h.writeUInt32LE(pcm.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, pcm]));
}

// Playwright's video starts before the script's clock. The video ends when the script ends, so the
// difference in length is the lead.
const leadOf = (take) => Math.max(0, take.videoMs - take.end);

// Merges the take's cuts into sorted, non-overlapping ranges of raw video time.
function rawCuts(take) {
  const lead = leadOf(take);
  const list = take.cuts.map((c) => [c.fromStart ? 0 : c.from + lead, c.to + lead]).sort((a, b) => a[0] - b[0]);
  const out = [];
  for (const c of list) {
    const last = out[out.length - 1];
    if (last && c[0] <= last[1]) last[1] = Math.max(last[1], c[1]);
    else if (c[1] > c[0]) out.push([...c]);
  }
  return out;
}

function keepRanges(cuts, total) {
  const out = [];
  let at = 0;
  for (const [a, b] of cuts) {
    if (a > at) out.push([at, a]);
    at = Math.max(at, b);
  }
  if (total > at) out.push([at, total]);
  return out;
}

function toOutput(rawMs, cuts) {
  const removed = cuts.reduce((sum, [a, b]) => sum + Math.max(0, Math.min(rawMs, b) - a), 0);
  return rawMs - removed;
}

// Builds the output timeline for all takes of a clip, in milliseconds.
function timeline(takes) {
  let base = 0;
  const captions = [];
  const steps = [];
  const pieces = [];
  for (const take of takes) {
    const lead = leadOf(take);
    const cuts = rawCuts(take);
    const keep = keepRanges(cuts, take.videoMs);
    const length = keep.reduce((sum, [a, b]) => sum + b - a, 0);
    for (const c of take.captions) {
      const raw = c.t + lead;
      if (cuts.some(([a, b]) => raw + c.ms > a && raw < b)) throw new Error(`${take.take}: a cut removes video under the line ${JSON.stringify(c.text)}`);
      captions.push({ ...c, at: base + toOutput(raw, cuts) });
    }
    for (const s of take.steps) steps.push({ ...s, at: base + toOutput(s.t + lead, cuts) });
    pieces.push({ take, keep, length });
    base += length;
  }
  captions.sort((a, b) => a.at - b.at);
  for (let i = 1; i < captions.length; i += 1) {
    const prev = captions[i - 1];
    if (prev.at + prev.ms > captions[i].at) throw new Error(`lines overlap by the clock: ${JSON.stringify(prev.text)} runs into ${JSON.stringify(captions[i].text)}`);
  }
  return { captions, steps, pieces, total: base };
}

function buildSpeech(file, captions, total) {
  const pcm = Buffer.alloc(Math.ceil(total / 1000 * RATE) * 2);
  for (const c of captions) {
    const clip = readPcm(c.wav);
    clip.copy(pcm, Math.round(c.at / 1000 * RATE) * 2);
  }
  writeWav(file, pcm);
}

// Measures, in the finished file, that each line's speech ends before the next begins.
function checkNoOverlap(clip, captions) {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-i', clip, '-af', 'silencedetect=noise=-40dB:d=0.1', '-f', 'null', '-'], { encoding: 'utf8', maxBuffer: 1 << 26 });
  const silences = [];
  let start = null;
  for (const line of r.stderr.split('\n')) {
    const a = line.match(/silence_start: ([\d.]+)/);
    const b = line.match(/silence_end: ([\d.]+)/);
    if (a) start = Number(a[1]);
    if (b && start !== null) { silences.push([start, Number(b[1])]); start = null; }
  }
  const problems = [];
  for (let i = 1; i < captions.length; i += 1) {
    const end = (captions[i - 1].at + captions[i - 1].ms) / 1000;
    const next = captions[i].at / 1000;
    // Allowance for the codec's own smearing at the edges of speech.
    const quiet = silences.some(([a, b]) => a < next + 0.12 && b > end - 0.12);
    if (!quiet) problems.push(`no silence between ${JSON.stringify(captions[i - 1].text)} and ${JSON.stringify(captions[i].text)}`);
  }
  return { lines: captions.length, boundaries: Math.max(0, captions.length - 1), silences: silences.length, problems };
}

function encodeClip({ name, takes, workDir, profile }) {
  const dir = path.join(workDir, 'clips');
  fs.mkdirSync(dir, { recursive: true });
  const tl = timeline(takes);
  const tag = `${name}-${profile.width}w-${profile.fps}f-${profile.crf}c-${profile.audio}k`;
  const out = path.join(dir, `${tag}.webm`);
  const wav = path.join(dir, `${name}-speech.wav`);
  buildSpeech(wav, tl.captions, tl.total);
  const inputs = tl.pieces.flatMap((p) => ['-i', p.take.raw]);
  const filters = tl.pieces.map((p, i) => {
    const pick = p.keep.map(([a, b]) => `between(t\\,${a / 1000}\\,${b / 1000})`).join('+');
    return `[${i}:v]fps=${profile.fps},select='${pick}',setpts=N/${profile.fps}/TB,scale=${profile.width}:-2:flags=lanczos,setsar=1[v${i}]`;
  });
  const parts = tl.pieces.map((_, i) => `[v${i}]`).join('');
  filters.push(`${parts}concat=n=${tl.pieces.length}:v=1:a=0[v]`);
  // Re-encoding is the slow part, so a clip newer than every take it came from is kept.
  const fresh = fs.existsSync(out) && takes.every((t) => fs.statSync(t.jsonPath).mtimeMs < fs.statSync(out).mtimeMs);
  if (!fresh) execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...inputs, '-i', wav,
    '-filter_complex', filters.join(';'), '-map', '[v]', '-map', `${tl.pieces.length}:a`,
    '-c:v', 'libvpx-vp9', '-crf', String(profile.crf), '-b:v', '0', '-row-mt', '1', '-cpu-used', '2', '-g', String(profile.fps * 8), '-tune-content', 'screen',
    '-c:a', 'libopus', '-b:a', `${profile.audio}k`, '-application', 'voip', '-ac', '1',
    out], { stdio: 'inherit' });
  const speech = checkNoOverlap(out, tl.captions);
  return { file: out, bytes: fs.statSync(out).size, seconds: tl.total / 1000, steps: tl.steps, captions: tl.captions, speech };
}

module.exports = { encodeClip, timeline };
