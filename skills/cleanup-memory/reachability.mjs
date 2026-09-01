#!/usr/bin/env node
// Reachability checker for /cleanup-memory Step 2 - one script so orphan
// counts are deterministic instead of reinvented per run (see SKILL.md).
// Usage: node reachability.mjs <memory-dir> [--line-cap=200]
// Resolves [[token]]/(file.md) links against a target's frontmatter `name:` OR basename.

import { readFileSync, readdirSync } from 'node:fs';
import { join, basename } from 'node:path';

function parseArgs(argv) {
  const dir = argv[2];
  if (!dir) {
    console.error('usage: node reachability.mjs <memory-dir> [--line-cap=N]');
    process.exit(2);
  }
  let lineCap = 200;
  for (const arg of argv.slice(3)) {
    const m = /^--line-cap=(\d+)$/.exec(arg);
    if (m) lineCap = Number(m[1]);
  }
  return { dir, lineCap };
}

function frontmatterName(text) {
  const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  if (!fm) return null;
  const nameLine = /^name:\s*(.+)$/m.exec(fm[1]);
  return nameLine ? nameLine[1].trim().replace(/^["']|["']$/g, '') : null;
}

// Any subdirectory other than archive/ is a demotion tier (e.g. cold/):
// files there are deliberately unindexed and must never be flagged as
// orphan-file or proposed for re-indexing.
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
  const parenRe = /\[[^\]]*\]\(([^)]+\.md)\)/g;
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
  const { dir, lineCap } = parseArgs(process.argv);
  const memoryMdPath = join(dir, 'MEMORY.md');
  const memoryMdFull = readFileSync(memoryMdPath, 'utf8');
  const memoryMdLines = memoryMdFull.split(/\r?\n/);
  const memoryMdLoaded = memoryMdLines.slice(0, lineCap).join('\n');

  const { live, demoted } = collectFiles(dir);
  const targets = buildTargets(live);

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
  const orphanFilesLoaded = live.filter((f) => !loadedResolved.has(f));

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
  const orphanFilesBfs = live.filter((f) => !visited.has(f));

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
  const orphanFilesAny = live.filter((f) => !reachableAny.has(f));

  const lines = [];
  lines.push(`memory dir: ${dir}`);
  lines.push(`line cap: ${lineCap}`);
  lines.push(`live files: ${live.length}`);
  lines.push(`demoted files (excluded from all readings): ${demoted.length}`);
  if (demoted.length) demoted.forEach((f) => lines.push(`  ${f}`));
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
