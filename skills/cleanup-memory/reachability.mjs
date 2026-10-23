#!/usr/bin/env node
// Reachability checker for /cleanup-memory Step 2 - one script so orphan
// counts are deterministic instead of reinvented per run (see SKILL.md).
// Usage: node reachability.mjs <memory-dir> [--byte-cap=N] [--line-cap=N]
// Resolves [[token]]/(file.md) links against a target's frontmatter `name:` OR basename.
//
// The loaded window is bounded by BYTES, not lines. A hardcoded 200-line default
// reported orphan-file: 0 on a 27.7KB index that was really dropping 31 files from
// line 134 on (2026-09-25), because the byte ceiling binds first on any index whose
// lines are long. The line cap is now derived from the byte cap; --line-cap still
// overrides it for a host with a genuinely different rule.

import { readFileSync, readdirSync } from 'node:fs';
import { join, basename } from 'node:path';

function parseArgs(argv) {
  const dir = argv[2];
  if (!dir) {
    console.error('usage: node reachability.mjs <memory-dir> [--byte-cap=N] [--line-cap=N]');
    process.exit(2);
  }
  let lineCap = null;
  let byteCap = Math.floor(24.4 * 1024);
  for (const arg of argv.slice(3)) {
    const l = /^--line-cap=(\d+)$/.exec(arg);
    if (l) lineCap = Number(l[1]);
    const b = /^--byte-cap=(\d+)$/.exec(arg);
    if (b) byteCap = Number(b[1]);
  }
  return { dir, lineCap, byteCap };
}

// The harness stops reading at a byte offset, so the effective line cap is wherever
// the running total crosses it. Counts the real terminator width: on a CRLF file a
// one-byte-per-line assumption undercounts by a byte per line, which is a ~150-byte
// error on a 150-line index and enough to put the cut on the wrong line.
function lineCapFromBytes(text, byteCap) {
  const eol = text.includes('\r\n') ? 2 : 1;
  let acc = 0;
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    acc += Buffer.byteLength(lines[i], 'utf8') + eol;
    if (acc > byteCap) return i;
  }
  return lines.length;
}

function frontmatterName(text) {
  const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  if (!fm) return null;
  const nameLine = /^name:\s*(.+)$/m.exec(fm[1]);
  return nameLine ? nameLine[1].trim().replace(/^["']|["']$/g, '') : null;
}

// Same reading as recall.py's parse_memory/_fm_value so both tools agree on what is superseded:
// the key counts at top level or indented (under `metadata:`), and an empty or quoted-empty
// value is absent. Only the frontmatter block is searched, never the body.
function isSuperseded(text) {
  const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  if (!fm) return false;
  const m = /^[ \t]*superseded_by:[ \t]*(.*?)[ \t]*$/m.exec(fm[1]);
  return Boolean(m && m[1].trim().replace(/^["']|["']$/g, '').trim());
}

// Any subdirectory other than archive/ is a demotion tier (e.g. cold/, rest/):
// files there are deliberately unindexed and must never be flagged as
// orphan-file or proposed for re-indexing. recall.py memory searches every tier.
// The always-loaded core (MEMORY.md) is capped at 8 KB; /cleanup-memory Step 1.7 demotes into a tier.
const CORE_CAP = 8192;

function collectFiles(dir) {
  const live = [];
  const demoted = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'MEMORY.md') continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'archive') continue;
      for (const sub of readdirSync(full, { withFileTypes: true })) {
        if (sub.isFile() && sub.name.endsWith('.md')) demoted.push(join(full, sub.name));
      }
      continue;
    }
    if (entry.isFile() && entry.name.endsWith('.md')) live.push(full);
  }
  return { live, demoted };
}

function buildTargets(files) {
  const targets = new Map();
  for (const f of files) {
    const text = readFileSync(f, 'utf8');
    const name = frontmatterName(text);
    const base = basename(f);
    if (name) targets.set(name, f);
    targets.set(base, f);
    targets.set(base.replace(/\.md$/, ''), f);
  }
  return targets;
}

function extractLinks(text) {
  const links = [];
  // Label tolerates one level of nested [..] (e.g. "#[cfg(test)]", "[hidden]") by
  // treating a balanced bracket pair as a single token in the label's alternation,
  // so a lone unmatched "]" is still what ends the label - greedy matching can
  // never cross it to glom two adjacent links together (todo 1039).
  const parenRe = /\[(?:[^[\]]|\[[^[\]]*\])*\]\(([^)]+\.md)\)/g;
  const wikiRe = /\[\[([^\]]+)\]\]/g;
  let m;
  while ((m = parenRe.exec(text))) links.push({ raw: m[1], kind: 'paren' });
  while ((m = wikiRe.exec(text))) links.push({ raw: m[1], kind: 'wiki' });
  return links;
}

function resolveLink(raw, targets) {
  const token = raw.trim();
  const base = basename(token);
  return targets.get(token) || targets.get(base) || targets.get(base.replace(/\.md$/, '')) || null;
}

function main() {
  const { dir, lineCap: lineCapArg, byteCap } = parseArgs(process.argv);
  const memoryMdPath = join(dir, 'MEMORY.md');
  const memoryMdFull = readFileSync(memoryMdPath, 'utf8');
  const memoryMdLines = memoryMdFull.split(/\r?\n/);
  const derivedCap = lineCapFromBytes(memoryMdFull, byteCap);
  const lineCap = lineCapArg ?? derivedCap;
  const capSource = lineCapArg === null ? `derived from --byte-cap=${byteCap}` : 'explicit --line-cap';
  const indexBytes = Buffer.byteLength(memoryMdFull, 'utf8');
  const memoryMdLoaded = memoryMdLines.slice(0, lineCap).join('\n');

  const { live, demoted } = collectFiles(dir);
  // Tier files stay link targets (an index line pointing at one is not dangling) but are
  // never in `live`, so no reading can call them orphan-file.
  // Demoted first so a live file wins a basename collision with a tier file.
  const targets = buildTargets([...demoted, ...live]);
  // Superseded files are unindexed on purpose: they stay link targets (so a link to one is
  // never an orphan-index-entry) but are never counted as orphan-file in any reading.
  const superseded = live.filter((f) => isSuperseded(readFileSync(f, 'utf8')));
  const isOrphanCandidate = (f) => !superseded.includes(f);

  // Reading C - "loaded-window, direct-link-only" (authoritative, per
  // SKILL.md Step 2): only (file.md) links inside MEMORY.md's own loaded
  // window count, since that is the only thing that ever reaches a session.
  const loadedParenLinks = extractLinks(memoryMdLoaded).filter((l) => l.kind === 'paren');
  const loadedResolved = new Set();
  const orphanIndexEntries = [];
  for (const link of loadedParenLinks) {
    const target = resolveLink(link.raw, targets);
    if (target) loadedResolved.add(target);
    else orphanIndexEntries.push(link.raw);
  }
  const orphanFilesLoaded = live.filter((f) => isOrphanCandidate(f) && !loadedResolved.has(f));

  // Reading B - strict BFS outward from MEMORY.md (full file, both link
  // kinds, transitive through memory files).
  const fullLinks = extractLinks(memoryMdFull);
  const visited = new Set();
  const queue = [];
  for (const link of fullLinks) {
    const target = resolveLink(link.raw, targets);
    if (target && !visited.has(target)) {
      visited.add(target);
      queue.push(target);
    }
  }
  while (queue.length) {
    const f = queue.shift();
    const text = readFileSync(f, 'utf8');
    for (const link of extractLinks(text)) {
      const target = resolveLink(link.raw, targets);
      if (target && !visited.has(target)) {
        visited.add(target);
        queue.push(target);
      }
    }
  }
  const orphanFilesBfs = live.filter((f) => isOrphanCandidate(f) && !visited.has(f));

  // Reading A - most lenient: any file crediting any other file with a
  // link counts as reachable, even a link from another orphan.
  const reachableAny = new Set();
  for (const link of fullLinks) {
    const target = resolveLink(link.raw, targets);
    if (target) reachableAny.add(target);
  }
  for (const f of live) {
    const text = readFileSync(f, 'utf8');
    for (const link of extractLinks(text)) {
      const target = resolveLink(link.raw, targets);
      if (target) reachableAny.add(target);
    }
  }
  const orphanFilesAny = live.filter((f) => isOrphanCandidate(f) && !reachableAny.has(f));

  const lines = [];
  lines.push(`memory dir: ${dir}`);
  lines.push(`index size: ${indexBytes} bytes across ${memoryMdLines.length} lines`);
  lines.push(`core index: ${indexBytes} / ${CORE_CAP} bytes${indexBytes > CORE_CAP ? ` OVER by ${indexBytes - CORE_CAP}` : ''}`);
  lines.push(`line cap: ${lineCap} (${capSource})`);
  if (lineCap < memoryMdLines.length) {
    lines.push(`  TRUNCATING: lines ${lineCap + 1}-${memoryMdLines.length} never reach a session`);
  }
  lines.push(`live files: ${live.length}`);
  lines.push(`demoted files (excluded from all readings): ${demoted.length}`);
  if (demoted.length) demoted.forEach((f) => lines.push(`  ${f}`));
  lines.push(`superseded (unindexed on purpose, excluded from every orphan-file reading): ${superseded.length}`);
  superseded.forEach((f) => lines.push(`    ${f}`));
  lines.push('');
  lines.push(`[authoritative] loaded-window, direct-link-only:`);
  lines.push(`  orphan-file: ${orphanFilesLoaded.length}`);
  orphanFilesLoaded.forEach((f) => lines.push(`    ${f}`));
  lines.push(`  orphan-index-entry: ${orphanIndexEntries.length}`);
  orphanIndexEntries.forEach((e) => lines.push(`    ${e}`));
  lines.push('');
  lines.push(`[context] strict-bfs-from-memory-md:`);
  lines.push(`  orphan-file: ${orphanFilesBfs.length}`);
  orphanFilesBfs.forEach((f) => lines.push(`    ${f}`));
  lines.push('');
  lines.push(`[context] any-file-credits-any-link:`);
  lines.push(`  orphan-file: ${orphanFilesAny.length}`);
  orphanFilesAny.forEach((f) => lines.push(`    ${f}`));

  console.log(lines.join('\n'));
}

main();
