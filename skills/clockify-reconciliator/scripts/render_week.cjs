#!/usr/bin/env node
// Renders the step 9a/13 week preview card: hero total on top, hour-by-hour
// timeline below. Same template every run - only --entries/--project/--target
// change the figures. See SKILL.md step 9a for the classification rules that
// produce the entries file this script consumes.
'use strict';
const fs = require('fs');
const { getArg } = require('./hs_common.cjs');

const args = process.argv.slice(2);
const entriesPath = getArg(args, '--entries');
const otherEntriesPath = getArg(args, '--other-entries'); // optional: other-project blocks, dashed lane, never counted
const outPath = getArg(args, '--out');
const project = getArg(args, '--project', 'Zirtue');
const weekStart = getArg(args, '--week-start');
const weekEnd = getArg(args, '--week-end');
const targetHours = parseFloat(getArg(args, '--target-hours', '0'));

if (!entriesPath || !outPath || !weekStart || !weekEnd) {
  console.error('Usage: render_week.cjs --entries <path.json> --out <out.html> --project <name> --week-start YYYY-MM-DD --week-end YYYY-MM-DD [--target-hours N] [--other-entries <path.json>]');
  process.exit(2);
}

// entries.json shape: [{date:"YYYY-MM-DD", start:"HH:MM", end:"HH:MM"|"24:00", desc, state:"old"|"new"|"edit"|"meeting", meetingKeyword?}]
const rawEntries = JSON.parse(fs.readFileSync(entriesPath, 'utf8'));
// other-entries.json shape: [{date:"YYYY-MM-DD", start:"HH:MM", end:"HH:MM"|"24:00"}] - no desc/state, never counted in any total
const rawOtherEntries = otherEntriesPath ? JSON.parse(fs.readFileSync(otherEntriesPath, 'utf8')) : [];

function toMin(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}
function fmtHM(min) {
  if (min <= 0) return '0h';
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  if (h === 0) return m + 'm';
  if (m === 0) return h + 'h';
  return h + 'h ' + m + 'm';
}
function fmtTimeMin(totalMin) {
  // 24-hour HH:MM, always zero-padded (2026-09-28: 12-hour am/pm read as
  // ambiguous next to the gutter's bare "9a"/"12p" labels).
  const hh = Math.floor(totalMin / 60) % 24, mm = totalMin % 60;
  return String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
}
function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function datesBetween(start, end) {
  const out = [];
  let d = new Date(start + 'T00:00:00Z');
  const endD = new Date(end + 'T00:00:00Z');
  while (d <= endD) {
    out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}
const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
function dayLabel(dateStr) {
  return DOW[new Date(dateStr + 'T00:00:00Z').getUTCDay()];
}
function dateLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00Z');
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return months[d.getUTCMonth()] + ' ' + d.getUTCDate();
}

const dates = datesBetween(weekStart, weekEnd);
function withMinutes(e) {
  const startMin = toMin(e.start);
  let endMin = toMin(e.end);
  if (endMin <= startMin) endMin += 24 * 60; // "24:00" or a genuine midnight-crossing block
  return { ...e, startMin, endMin, dur: endMin - startMin };
}
const entries = rawEntries.map(withMinutes);
const otherEntries = rawOtherEntries.map(withMinutes);

// per-day totals by state
const dayTotals = {};
for (const d of dates) dayTotals[d] = { old: 0, edit: 0, new: 0, meeting: 0 };
for (const e of entries) {
  if (!dayTotals[e.date]) dayTotals[e.date] = { old: 0, edit: 0, new: 0, meeting: 0 };
  dayTotals[e.date][e.state] = (dayTotals[e.date][e.state] || 0) + e.dur;
}

let totOld = 0, totEdit = 0, totNew = 0, totMeeting = 0;
for (const d of Object.values(dayTotals)) { totOld += d.old; totEdit += d.edit; totNew += d.new; totMeeting += d.meeting; }
const totalMin = totOld + totEdit + totNew + totMeeting;
const targetMin = targetHours * 60;

// grid bounds: floor(earliest start) .. ceil(latest end), across all entries (this project's and other-project's,
// since an other-project block outside this project's own hours would otherwise render off-grid)
let minStart = Infinity, maxEnd = -Infinity;
for (const e of entries.concat(otherEntries)) { minStart = Math.min(minStart, e.startMin); maxEnd = Math.max(maxEnd, e.endMin); }
if (!isFinite(minStart)) { minStart = 9 * 60; maxEnd = 18 * 60; } // empty week fallback
const GRID_START = Math.floor(minStart / 60) * 60;
const GRID_END = Math.ceil(maxEnd / 60) * 60;
const HOUR_PX = 34;
const gridHeight = ((GRID_END - GRID_START) / 60) * HOUR_PX;

function heroHtml() {
  // targetMin <= 0 means the caller's full-week gate (SKILL.md step 9a) failed for this window -
  // draw a neutral, non-progress ring so a partial/non-Monday-aligned window never implies a
  // target was tracked or met (2026-09-03 incident: a today-only fetch reported "to go this week").
  const hasTarget = targetMin > 0;
  const pct = hasTarget ? Math.min(100, (totalMin / targetMin) * 100) : 100;
  const r = 54, c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  const overTarget = hasTarget && totalMin > targetMin;
  const ringColor = !hasTarget ? '#4b5160' : overTarget ? '#e0a94c' : '#14b8a6';
  return `
  <div class="hero">
    <div class="hero-ring">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="${r}" fill="none" stroke="#232733" stroke-width="12"/>
        <circle cx="70" cy="70" r="${r}" fill="none" stroke="${ringColor}" stroke-width="12"
          stroke-dasharray="${dash} ${c - dash}" stroke-linecap="round"
          transform="rotate(-90 70 70)"/>
        <text x="70" y="64" text-anchor="middle" font-size="26" font-weight="700" fill="#e6e8ec">${fmtHM(totalMin)}</text>
        <text x="70" y="86" text-anchor="middle" font-size="11" fill="#7d8492">${hasTarget ? 'of ' + fmtHM(targetMin) + ' target' : 'this window'}</text>
      </svg>
    </div>
    <div class="hero-body">
      <div class="hero-title">${escHtml(project)} &middot; week of ${dateLabel(weekStart)}&ndash;${dateLabel(weekEnd)}</div>
      <div class="hero-chips">
        <span class="chip chip-old"><i class="ph ph-square"></i>Logged ${fmtHM(totOld)}</span>
        ${totEdit > 0 ? `<span class="chip chip-edit"><i class="ph ph-pencil-simple"></i>Filled in ${fmtHM(totEdit)}</span>` : ''}
        ${totNew > 0 ? `<span class="chip chip-new"><i class="ph ph-plus-circle"></i>Added this run ${fmtHM(totNew)}</span>` : ''}
        ${totMeeting > 0 ? `<span class="chip chip-meeting"><i class="ph ph-users-three"></i>Meetings ${fmtHM(totMeeting)}</span>` : ''}
      </div>
    </div>
  </div>`;
}

function timelineHtml() {
  // .v2-colbody must get the same explicit height as the gutter: its only content is
  // absolutely-positioned blocks, which don't contribute to a parent's height on their own, so
  // an unset height here collapses the column's real box below its visual content and the
  // blocks paint outside it (looks like overflow) instead of the column growing to fit.
  const dayCols = dates.map((d, di) => {
    const es = entries.filter(e => e.date === d);
    const blocks = es.map(e => {
      const top = ((e.startMin - GRID_START) / 60) * HOUR_PX;
      const height = (e.dur / 60) * HOUR_PX;
      const startLabel = fmtTimeMin(e.startMin), endLabel = fmtTimeMin(e.endMin);
      const meetingNote = e.state === 'meeting' && e.meetingKeyword ? ` [keyword: ${escHtml(e.meetingKeyword)}]` : '';
      const tip = `${startLabel}-${endLabel} (${e.dur}min)\n${escHtml(e.desc)}${meetingNote}`;
      // Under ~26px there's no room for the description; under ~14px not even the time range.
      // Line-clamp the desc to however many lines actually fit (9px font * 1.15 line-height,
      // minus the 4px vertical padding and the time line) instead of letting overflow:hidden
      // hard-cut mid-word with no ellipsis (2026-09-28 finding: the Tue 7:30-8:20pm block above
      // clipped "...triggers across the v2 flow" with no indication anything was missing).
      const descLines = Math.max(1, Math.floor((height - 4 - 10.35) / 10.35));
      const inner = height >= 26
        ? `<span class="v2-time">${startLabel}-${endLabel}</span><span class="v2-desc" style="-webkit-line-clamp:${descLines};display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden;">${escHtml(e.desc)}</span>`
        : height >= 14
          ? `<span class="v2-time">${startLabel}-${endLabel}</span>`
          : '';
      // The hover tooltip is a tiny block's ONLY way to show its info (SKILL.md step 9a), which
      // makes tooltip clipping a real bug, not a cosmetic one. `.v2-cal`'s overflow-x:auto also
      // computes overflow-y to 'auto' (CSS overflow spec), so a tooltip that pops past the grid's
      // own edge gets silently cut off with no scroll affordance visible - exactly the case for a
      // short meeting/task block sitting near the day's last hour (2026-09-30 finding: the Mon
      // 18:00-18:20 standup and the 18:20-18:35 block right after it were both unreadable on
      // hover). Flip the anchor per block instead of always opening down-right.
      const tipUp = (top + height / 2) > (gridHeight / 2) ? ' v2-tip-up' : '';
      const tipLeft = di >= dates.length - 2 ? ' v2-tip-left' : '';
      // The truncating overflow:hidden must live on an INNER wrapper, not on .v2-block itself -
      // .v2-block is what :hover triggers on and what the ::after tooltip is a child of, and a
      // parent's overflow:hidden clips its own pseudo-element descendants even when they're
      // position:absolute (2026-09-30 finding: the up/left anchor-flip above did nothing because
      // the tooltip never escaped its own block's box in ANY direction - overflow:hidden on
      // .v2-block was clipping it at the source, before the .v2-cal scroll container even mattered).
      return `<div class="v2-block v2-${e.state}${tipUp}${tipLeft}" style="top:${top}px;height:${height}px" data-tip="${tip}"><div class="v2-block-inner">${inner}</div></div>`;
    }).join('');
    const otherBlocks = otherEntries.filter(e => e.date === d).map(e => {
      const top = ((e.startMin - GRID_START) / 60) * HOUR_PX;
      const height = (e.dur / 60) * HOUR_PX;
      return `<div class="v2-other-block" style="top:${top}px;height:${height}px" title="other project"></div>`;
    }).join('');
    const t = dayTotals[d] || { old: 0, edit: 0, new: 0, meeting: 0 };
    const total = t.old + t.edit + t.new + t.meeting;
    return `<div class="v2-col"><div class="v2-colhead"><span class="v2-dname">${dayLabel(d)}</span><span class="v2-ddate">${dateLabel(d)}</span><span class="v2-dtot">${total > 0 ? fmtHM(total) : '-'}</span></div><div class="v2-colbody" style="height:${gridHeight}px">${blocks}<div class="v2-other-lane">${otherBlocks}</div></div></div>`;
  }).join('');

  let hourLabels = '';
  for (let m = GRID_START; m < GRID_END; m += 60) {
    const top = ((m - GRID_START) / 60) * HOUR_PX;
    const hh = (m / 60) % 24;
    const label = String(hh).padStart(2, '0');
    hourLabels += `<div class="v2-hourlabel" style="top:${top}px">${label}</div>`;
  }

  const startH = Math.floor(GRID_START / 60), endH = Math.ceil(GRID_END / 60);
  const startLabel = fmtTimeMin(GRID_START);
  const endLabel = GRID_END % 1440 === 0 ? '24:00' : fmtTimeMin(GRID_END);

  return `
      <div class="v2-cal">
        <div class="v2-gutter">
          <div class="v2-colhead" style="visibility:hidden"><span class="v2-dname">&nbsp;</span><span class="v2-ddate">&nbsp;</span><span class="v2-dtot">&nbsp;</span></div>
          <div class="v2-hourcol" style="height:${gridHeight}px">${hourLabels}</div>
        </div>
        <div class="v2-cols">${dayCols}</div>
      </div>
      <div class="footer">Showing ${startLabel} to ${endLabel}, empty hours outside that range are cropped.</div>`;
}

const html = `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="color-scheme" content="dark">
<meta name="darkreader-lock">
<title>${escHtml(project)} week preview</title>
<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web"></link>
<style>
  * { box-sizing: border-box; }
  html { scrollbar-width:thin; scrollbar-color:#363c48 #0b0d11; }
  html::-webkit-scrollbar { width:10px; }
  html::-webkit-scrollbar-track { background:#0b0d11; }
  html::-webkit-scrollbar-thumb { background:#363c48; border-radius:8px; border:2px solid #0b0d11; }
  html::-webkit-scrollbar-thumb:hover { background:#454c5a; }
  body { margin:0; background:#0b0d11; color:#e6e8ec; font-family:-apple-system,Segoe UI,Roboto,sans-serif; padding:24px; }
  .card { border:1px solid #262a33; border-radius:10px; padding:20px; background:#0f1115; max-width:1300px; }

  .hero { display:flex; gap:22px; align-items:center; padding-bottom:18px; border-bottom:1px solid #20242d; margin-bottom:18px; }
  .hero-title { font-size:15px; font-weight:600; }
  .hero-target { font-size:12.5px; color:#7d8492; margin:2px 0 10px; }
  .hero-target .over { color:#e0a94c; }
  .hero-chips { display:flex; gap:10px; flex-wrap:wrap; }
  .chip { display:inline-flex; align-items:center; gap:5px; font-size:11.5px; padding:4px 9px; border-radius:12px; background:#1a1e26; color:#c3c8d1; }
  .chip i { font-size:12px; }
  .chip-new { color:#5eead4; }
  .chip-edit { color:#8fb8ff; }
  .chip-meeting { color:#c9b6f5; }

  .legend { display:flex; gap:16px; margin-top:14px; font-size:12px; color:#c3c8d1; }
  .legend-item { display:flex; align-items:center; gap:6px; }
  .sw { width:11px; height:11px; border-radius:2px; display:inline-block; }
  .sw-old { background:#3f7a56; }
  .sw-edit { background:#3b6bb0; }
  .sw-new { background:#14b8a6; }
  .sw-meeting { background: repeating-linear-gradient(45deg,#7c5cbf,#7c5cbf 3px,#6a4aab 3px,#6a4aab 6px); }
  .sw-other { background:transparent; border:1px dashed #4a4f5c; }

  .v2-cal { display:flex; border:1px solid #20242d; border-radius:8px; overflow-x:auto; scrollbar-width:thin; scrollbar-color:#363c48 #12151b; }
  .v2-cal::-webkit-scrollbar { height:8px; }
  .v2-cal::-webkit-scrollbar-track { background:#12151b; border-radius:8px; }
  .v2-cal::-webkit-scrollbar-thumb { background:#363c48; border-radius:8px; border:2px solid #12151b; }
  .v2-cal::-webkit-scrollbar-thumb:hover { background:#454c5a; }
  .v2-gutter { width:40px; flex-shrink:0; position:sticky; left:0; z-index:1; background:#12151b; }
  .v2-hourcol { position:relative; }
  .v2-hourlabel { position:absolute; right:6px; transform:translateY(-6px); font-size:9px; color:#5b616d; }
  .v2-cols { display:flex; flex:1; min-width:760px; }
  .v2-col { flex:1; border-left:1px solid #191d24; position:relative; }
  .v2-colhead { display:flex; flex-direction:column; padding:6px 6px 4px; background:#12151b; border-bottom:1px solid #20242d; }
  .v2-dname { font-size:11px; font-weight:700; }
  .v2-ddate { font-size:9px; color:#5b616d; }
  .v2-dtot { font-size:10.5px; color:#5fd99a; font-weight:600; margin-top:1px; }
  .v2-colbody { position:relative; }
  .v2-block { position:absolute; left:2px; right:10px; border-radius:3px; font-size:9px; line-height:1.15; cursor:default; }
  .v2-block-inner { height:100%; padding:2px 4px; overflow:hidden; }
  .v2-old { background:#2d5940; color:#cfe8da; }
  .v2-edit { background:#274870; border-left:3px solid #8fb8ff; color:#dbe8fb; }
  .v2-new { background:#0f7a6e; border-left:3px solid #5eead4; color:#d6fbf5; }
  .v2-meeting { background: repeating-linear-gradient(45deg,#5b4390,#5b4390 4px,#4a3577 4px,#4a3577 8px); color:#ece6fb; }
  .v2-time { display:block; font-weight:600; opacity:0.85; }
  .v2-desc { display:block; }
  .v2-other-lane { position:absolute; top:0; right:0; bottom:0; width:6px; }
  .v2-other-block { position:absolute; left:0; right:0; border:1px dashed #4a4f5c; border-radius:2px; background:transparent; }
  .v2-block[data-tip]:hover::after {
    content: attr(data-tip); white-space: pre-line; position:absolute; left:105%; top:0; z-index:10;
    background:#1c1f27; border:1px solid #333a47; color:#e6e8ec; padding:8px 10px; border-radius:6px;
    font-size:11px; width:220px; box-shadow: 0 6px 20px rgba(0,0,0,0.5);
  }
  .v2-block.v2-tip-up[data-tip]:hover::after { top:auto; bottom:0; }
  .v2-block.v2-tip-left[data-tip]:hover::after { left:auto; right:105%; }
  .footer { margin-top:10px; font-size:11px; color:#7d8492; }
</style>
</head>
<body>
  <div class="card">
    ${heroHtml()}
    ${timelineHtml()}
    <div class="legend">
      <div class="legend-item"><span class="sw sw-old"></span>Logged</div>
      ${totEdit > 0 ? `<div class="legend-item"><span class="sw sw-edit"></span>Filled in</div>` : ''}
      ${totNew > 0 ? `<div class="legend-item"><span class="sw sw-new"></span>Added this run</div>` : ''}
      ${totMeeting > 0 ? `<div class="legend-item"><span class="sw sw-meeting"></span>Meeting</div>` : ''}
      ${otherEntries.length > 0 ? `<div class="legend-item"><span class="sw sw-other"></span>Other project (not counted)</div>` : ''}
    </div>
  </div>
</body></html>`;

fs.writeFileSync(outPath, html);
console.log(JSON.stringify({ ok: true, out: outPath, totalMin, targetMin, bytes: html.length }));
