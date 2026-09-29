#!/usr/bin/env node
// Renders the /iterate-it final report card: the verdict open on top, everything
// else (score chart, round-by-round, risk, rejected ideas, run stats) collapsed
// below it. Same template every run - only the run JSON changes. See SKILL.md
// "Output" for the JSON shape and when this runs.
'use strict';
const fs = require('fs');

function getArg(args, name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback;
}

const args = process.argv.slice(2);
const runPath = getArg(args, '--run');
const outPath = getArg(args, '--out');
if (!runPath || !outPath) {
  console.error('Usage: render_report.cjs --run <run.json> --out <out.html>');
  process.exit(2);
}

// run.json shape:
// { hypothesis, answer, score, audit, threshold, floor,
//   ended: { phase: "Explore"|"Polish", round, reason: "floor"|"cap"|"thrash"|<free text> },
//   solution: [string], dissent?: string, risk?: string, rejected?: [string], tokens?: number,
//   rounds: [{ n, phase, angle, score, audit, marker: "REVISION"|"PIVOT"|"KILL", change,
//              risk?, reverted?: bool, proposal? }] }
const run = JSON.parse(fs.readFileSync(runPath, 'utf8'));
const rounds = run.rounds || [];
const threshold = run.threshold ?? 7;
const floor = run.floor ?? 9;

function escHtml(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function scoreColor(s) {
  if (s >= floor) return '#14b8a6';
  if (s >= threshold) return '#e0a94c';
  return '#e06c6c';
}
const REASONS = { floor: 'floor hit', cap: 'round cap hit', thrash: 'unconverged, 3 pivots/kills in a row' };
const reasonLabel = REASONS[run.ended?.reason] || run.ended?.reason || '';
const converged = run.ended?.reason !== 'thrash';

function heroHtml() {
  const color = scoreColor(run.score);
  const dissent = run.dissent
    ? `<div class="dissent"><i class="ph ph-warning"></i><div><b>Main dissent:</b> subagent ${escHtml(run.score)}/10, Claude's audit ${escHtml(run.audit)}/10. ${escHtml(run.dissent)}</div></div>`
    : '';
  return `
  <div class="hero">
    <div class="score" style="border-color:${color};color:${color}">${escHtml(run.score)}<span>/10</span></div>
    <div class="hero-body">
      <div class="answer">${escHtml(run.answer)}</div>
      <div class="chips">
        <span class="chip"><i class="ph ph-flag-checkered"></i>Ended: ${escHtml(run.ended?.phase)} round ${escHtml(run.ended?.round)}</span>
        <span class="chip ${converged ? '' : 'chip-bad'}"><i class="ph ${converged ? 'ph-check-circle' : 'ph-x-circle'}"></i>${escHtml(reasonLabel)}</span>
      </div>
    </div>
  </div>
  ${dissent}
  <div class="section-label">Final solution</div>
  <ul class="solution">${(run.solution || []).map(b => `<li>${escHtml(b)}</li>`).join('')}</ul>`;
}

function chartSvg() {
  if (rounds.length === 0) return '<div class="muted">No rounds recorded.</div>';
  const W = 620, H = 170, padL = 28, padR = 12, padT = 10, padB = 24;
  const n = rounds.length;
  const x = i => padL + (n === 1 ? (W - padL - padR) / 2 : (i * (W - padL - padR)) / (n - 1));
  const y = s => padT + ((10 - s) * (H - padT - padB)) / 10;
  const line = key => rounds.map((r, i) => `${x(i)},${y(r[key])}`).join(' ');
  const guide = (s, label, color) =>
    `<line x1="${padL}" x2="${W - padR}" y1="${y(s)}" y2="${y(s)}" stroke="${color}" stroke-dasharray="4 4" stroke-width="1"/>` +
    `<text x="${W - padR}" y="${y(s) - 4}" text-anchor="end" font-size="9.5" fill="${color}">${label} ${s}</text>`;
  const polishStart = rounds.findIndex(r => r.phase === 'Polish');
  const divider = polishStart > 0
    ? `<line x1="${(x(polishStart - 1) + x(polishStart)) / 2}" x2="${(x(polishStart - 1) + x(polishStart)) / 2}" y1="${padT}" y2="${H - padB}" stroke="#3a4050" stroke-width="1"/>` +
      `<text x="${(x(polishStart - 1) + x(polishStart)) / 2 + 4}" y="${padT + 10}" font-size="9.5" fill="#7d8492">Polish</text>`
    : '';
  const dots = rounds.map((r, i) =>
    `<circle cx="${x(i)}" cy="${y(r.score)}" r="4" fill="${scoreColor(r.score)}"><title>R${r.n} ${escHtml(r.phase)}: ${r.score}/10 (audit ${r.audit})</title></circle>` +
    `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="9.5" fill="#7d8492">R${r.n}</text>`).join('');
  const yLabels = [0, 5, 10].map(s => `<text x="${padL - 6}" y="${y(s) + 3}" text-anchor="end" font-size="9.5" fill="#5b616d">${s}</text>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px">
    ${yLabels}${guide(threshold, 'threshold', '#6b5a33')}${guide(floor, 'floor', '#1f6b62')}${divider}
    <polyline points="${line('audit')}" fill="none" stroke="#8fb8ff" stroke-width="1.5" stroke-dasharray="3 3"/>
    <polyline points="${line('score')}" fill="none" stroke="#c3c8d1" stroke-width="2"/>
    ${dots}
  </svg>
  <div class="legend"><span><i class="sw sw-sub"></i>Subagent score</span><span><i class="sw sw-audit"></i>Claude's audit</span></div>
  <div class="muted">${rounds.map(r => r.score).join(' → ')} (audit ${rounds.map(r => r.audit).join(' → ')})</div>`;
}

function roundsHtml() {
  return rounds.map(r => `
    <details class="round">
      <summary><span class="rn">R${escHtml(r.n)}</span><span class="rphase">${escHtml(r.phase)} · ${escHtml(r.angle)}</span>
        <span class="rscore" style="color:${scoreColor(r.score)}">${escHtml(r.score)}/10</span><span class="raudit">audit ${escHtml(r.audit)}</span>
        <span class="marker m-${escHtml(String(r.marker).toLowerCase())}">${escHtml(r.marker)}</span>${r.reverted ? '<span class="marker m-kill">REVERTED</span>' : ''}
        <span class="rchange">${escHtml(r.change)}</span></summary>
      <div class="rbody">
        ${r.risk ? `<div><b>Highest-risk assumption:</b> ${escHtml(r.risk)}</div>` : ''}
        ${r.proposal ? `<div class="proposal">${escHtml(r.proposal)}</div>` : ''}
      </div>
    </details>`).join('');
}

function group(title, icon, body) {
  return `<details class="group"><summary><i class="ph ${icon}"></i>${title}</summary><div class="gbody">${body}</div></details>`;
}

const stats = [
  `${rounds.length} rounds: ${rounds.filter(r => r.phase === 'Explore').length} explore + ${rounds.filter(r => r.phase === 'Polish').length} polish`,
  `Threshold ${threshold}, floor ${floor}`,
  run.tokens ? `Subagent tokens: ~${Math.round(run.tokens / 1000)}k` : null,
].filter(Boolean).map(s => `<li>${escHtml(s)}</li>`).join('');

const html = `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="color-scheme" content="dark">
<meta name="darkreader-lock">
<title>iterate-it report</title>
<script src="https://unpkg.com/@phosphor-icons/web"></script>
<style>
  * { box-sizing: border-box; }
  html { scrollbar-width:thin; scrollbar-color:#363c48 #0b0d11; }
  body { margin:0; background:#0b0d11; color:#e6e8ec; font-family:-apple-system,Segoe UI,Roboto,sans-serif; padding:24px; font-size:13.5px; line-height:1.45; }
  .card { border:1px solid #262a33; border-radius:10px; padding:20px; background:#0f1115; max-width:900px; }
  .hero { display:flex; gap:18px; align-items:center; }
  .score { flex-shrink:0; width:92px; height:92px; border:5px solid; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:34px; font-weight:700; }
  .score span { font-size:13px; font-weight:500; opacity:0.7; margin-top:10px; }
  .answer { font-size:16px; font-weight:600; margin-bottom:8px; }
  .chips { display:flex; gap:8px; flex-wrap:wrap; }
  .chip { display:inline-flex; align-items:center; gap:5px; font-size:11.5px; padding:4px 9px; border-radius:12px; background:#1a1e26; color:#c3c8d1; }
  .chip-bad { color:#e06c6c; }
  .dissent { display:flex; gap:10px; margin-top:16px; padding:10px 12px; border-radius:8px; background:#2a1f12; border:1px solid #6b5a33; color:#f0d9a8; }
  .dissent i { font-size:18px; color:#e0a94c; }
  .section-label { margin-top:18px; font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:#7d8492; }
  .solution { margin:6px 0 0; padding-left:20px; }
  .solution li { margin:4px 0; }
  .group { margin-top:10px; border:1px solid #20242d; border-radius:8px; background:#12151b; }
  .group > summary { cursor:pointer; padding:9px 12px; font-weight:600; display:flex; align-items:center; gap:8px; list-style:none; }
  .group > summary::before { content:'▸'; color:#7d8492; transition:transform .15s; }
  .group[open] > summary::before { transform:rotate(90deg); }
  .groups { margin-top:20px; }
  .gbody { padding:4px 12px 12px; }
  .gbody ul { margin:0; padding-left:20px; }
  .muted { color:#7d8492; font-size:12px; margin-top:4px; }
  .legend { display:flex; gap:14px; font-size:11.5px; color:#c3c8d1; margin-top:4px; }
  .sw { display:inline-block; width:14px; height:0; border-top:2px solid; margin-right:5px; vertical-align:middle; }
  .sw-sub { border-color:#c3c8d1; }
  .sw-audit { border-color:#8fb8ff; border-top-style:dashed; }
  .round { border-top:1px solid #1d2129; }
  .round:first-child { border-top:none; }
  .round > summary { cursor:pointer; padding:7px 0; display:flex; flex-wrap:wrap; gap:8px; align-items:baseline; list-style:none; }
  .rn { font-weight:700; width:24px; }
  .rphase { color:#9aa1ad; font-size:12px; }
  .rscore { font-weight:700; }
  .raudit { color:#8fb8ff; font-size:12px; }
  .rchange { flex-basis:100%; padding-left:32px; color:#c3c8d1; }
  .marker { font-size:10px; padding:1px 6px; border-radius:8px; background:#1a1e26; color:#9aa1ad; }
  .m-pivot { color:#e0a94c; }
  .m-kill { color:#e06c6c; }
  .rbody { padding:0 0 10px 32px; color:#c3c8d1; }
  .proposal { margin-top:6px; white-space:pre-wrap; padding:8px 10px; border-left:2px solid #2d3340; background:#0f1115; }
</style>
</head>
<body>
  <div class="card">
    ${heroHtml()}
    <div class="groups">
      ${group('Score evolution', 'ph-chart-line-up', chartSvg())}
      ${group('Round by round', 'ph-list-numbers', roundsHtml() || '<div class="muted">No rounds recorded.</div>')}
      ${run.risk ? group('Biggest remaining risk', 'ph-warning-diamond', `<div>${escHtml(run.risk)}</div>`) : ''}
      ${(run.rejected || []).length ? group('Rejected, never re-propose', 'ph-prohibit', `<ul>${run.rejected.map(r => `<li>${escHtml(r)}</li>`).join('')}</ul>`) : ''}
      ${group('Run stats', 'ph-gauge', `<ul>${stats}</ul><div class="section-label">Original hypothesis</div><div class="proposal">${escHtml(run.hypothesis)}</div>`)}
    </div>
  </div>
</body></html>`;

fs.writeFileSync(outPath, html);
console.log(JSON.stringify({ ok: true, out: outPath, rounds: rounds.length, bytes: html.length }));
