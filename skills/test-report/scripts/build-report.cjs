// Builds the one self-contained report page from recorded takes and a report file holding only the
// words. Usage: node build-report.cjs <report.cjs> <workDir> <out.html>
const fs = require('fs');
const path = require('path');
const { encodeClip } = require('./encode.cjs');

// The panel refuses a page over 8MiB (8388608): MAX_HTML_BYTES in Conductor's daemon/preview.rs. This leaves it ~388KB.
const MAX_BYTES = 8000000;
const LADDER = [
  { width: 1280, fps: 10, crf: 40, audio: 24 },
  { width: 1000, fps: 8, crf: 46, audio: 16 },
  { width: 1000, fps: 8, crf: 50, audio: 14 },
  { width: 960, fps: 6, crf: 52, audio: 12 },
  { width: 860, fps: 5, crf: 54, audio: 10 },
];

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const fmt = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;

const [reportFile, workDirArg, outArg] = process.argv.slice(2);
if (!outArg) { console.error('usage: node build-report.cjs <report.cjs> <workDir> <out.html>'); process.exit(2); }
const report = require(path.resolve(reportFile));
const workDir = path.resolve(workDirArg);
const out = path.resolve(outArg);
const template = fs.readFileSync(path.join(__dirname, 'template.html'), 'utf8');
const loadTake = (name) => {
  const jsonPath = path.join(workDir, 'takes', `${name}.json`);
  return { ...JSON.parse(fs.readFileSync(jsonPath, 'utf8')), jsonPath };
};

function stepList(steps) {
  const rows = steps.map((s) => {
    const t = Math.max(0, s.at / 1000);
    return `<li><button class="jump${s.ok ? '' : ' failed'}" data-t="${t.toFixed(1)}"><span class="time">${fmt(t)}</span><span>${esc(s.name)}<span class="res">${s.ok ? 'Passed' : `Failed: ${esc(s.error || '')}`}</span></span></button></li>`;
  });
  return `<ol class="steps">${rows.join('')}</ol>`;
}

// Each ticket is { label, url }. Tickets get their own card instead of crowding the heading.
function ticketCard(tickets) {
  if (!tickets || !tickets.length) return '';
  return `<div class="tickets"><h2>Tickets</h2>${tickets.map((t) => `<a href="${esc(t.url)}">${esc(t.label)}</a>`).join('')}</div>`;
}

function player(src) {
  return `<div class="player"><video preload="auto" playsinline src="${src}"></video><div class="bar"><button class="play" aria-label="Play or pause">Play</button><input class="seek" type="range" min="0" max="1" step="0.1" value="0" aria-label="Position in the video"><span class="clock">0:00</span><button class="speed" aria-label="Playback speed">1x</button><button class="sound" aria-label="Turn sound on or off">Sound on</button><button class="full" aria-label="Full screen">Full screen</button></div></div>`;
}

function build(profile) {
  const clips = {};
  for (const slide of report.slides) {
    if (slide.takes) clips[slide.clip] = encodeClip({ name: slide.clip, takes: slide.takes.map(loadTake), workDir, profile });
  }
  const all = Object.values(clips).flatMap((c) => c.steps);
  const failed = all.filter((s) => !s.ok);
  const headline = failed.length
    ? `${failed.length} of ${all.length} recorded steps failed`
    : `Nothing is broken. All ${all.length} recorded steps passed.`;
  const failedBox = failed.length
    ? `<div class="box bad"><h2>What failed</h2><ul>${failed.map((s) => `<li>${esc(s.name)}: ${esc(s.error || '')}</li>`).join('')}</ul></div>`
    : '';
  const sections = report.slides.map((slide) => {
    const body = (slide.html || '').replace(/\{\{HEADLINE\}\}/g, esc(headline)).replace(/\{\{FAILED\}\}/g, failedBox);
    if (!slide.takes) return `<section data-title="${esc(slide.title)}">${body}${ticketCard(slide.tickets)}</section>`;
    const c = clips[slide.clip];
    const src = `data:video/webm;base64,${fs.readFileSync(c.file).toString('base64')}`;
    return `<section data-title="${esc(slide.title)}">${body}<div class="watch">${player(src)}<div class="side">${stepList(c.steps)}${ticketCard(slide.tickets)}</div></div></section>`;
  }).join('\n');
  // A function replacement, so a $ in the words or the base64 is not read as a replacement pattern.
  const html = template.replace('{{TITLE}}', () => esc(report.title)).replace('{{SECTIONS}}', () => sections);
  return { html, clips, all, failed };
}

let result = null;
let used = null;
for (const profile of LADDER) {
  result = build(profile);
  used = profile;
  const bytes = Buffer.byteLength(result.html);
  console.log(`profile ${JSON.stringify(profile)}: ${bytes} bytes`);
  if (bytes <= MAX_BYTES) break;
}
const bytes = Buffer.byteLength(result.html);
const problems = Object.entries(result.clips).flatMap(([name, c]) => c.speech.problems.map((p) => `${name}: ${p}`));
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, result.html);
for (const [name, c] of Object.entries(result.clips)) {
  console.log(`clip ${name}: ${c.seconds.toFixed(0)}s, ${c.bytes} bytes, ${c.speech.lines} lines, ${c.speech.boundaries} boundaries measured, ${c.speech.problems.length} overlaps`);
}
console.log(`deck ${out}: ${bytes} bytes, ${result.all.length} steps, ${result.failed.length} failed, profile ${JSON.stringify(used)}`);
if (problems.length) { console.error(`OVERLAP\n${problems.join('\n')}`); process.exit(3); }
if (bytes > MAX_BYTES) { console.error(`TOO BIG for the panel even at the lowest quality: ${bytes} bytes over ${MAX_BYTES}. Cut narration or split into two reports.`); process.exit(4); }
