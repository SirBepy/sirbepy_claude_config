// Build a "work recap" presentation + embedded PR explorer from a config file.
// Fetches each PR's metadata + unified diff via `gh`, parses the diff per file,
// injects everything into template.html (same folder), and writes the output HTML.
//
//   node build-deck.mjs <config.json> [output.html]
//
// Run from inside the target git repo (so `gh` resolves the right repo), OR set
// "repo": "owner/name" in the config. See SKILL.md for the config schema.
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, isAbsolute, resolve } from 'node:path';

const DIR = dirname(fileURLToPath(import.meta.url));

const configPath = process.argv[2];
if (!configPath) { process.stderr.write('usage: node build-deck.mjs <config.json> [output.html]\n'); process.exit(1); }
const outArg = process.argv[3] || 'work-recap-deck.html';
const outPath = isAbsolute(outArg) ? outArg : resolve(process.cwd(), outArg);

const META = JSON.parse(readFileSync(resolve(process.cwd(), configPath), 'utf8'));
const repoFlag = META.repo ? ` --repo ${META.repo}` : '';

const sh = (cmd) => execSync(cmd, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });

function parseDiff(diff) {
  const files = {};
  const chunks = diff.split(/^diff --git /m).slice(1);
  for (const chunk of chunks) {
    const lines = chunk.split('\n');
    let path = null, binary = false;
    const hm = lines[0].match(/ b\/(.+)$/) || lines[0].match(/^a\/(\S+)/);
    if (hm) path = hm[1];
    const body = [];
    let inBody = false;
    for (let i = 1; i < lines.length; i++) {
      const l = lines[i];
      if (l.startsWith('Binary files')) { binary = true; break; }
      if (l.startsWith('+++ ')) { const m = l.match(/^\+\+\+ b\/(.+)$/); if (m) path = m[1]; inBody = true; continue; }
      if (l.startsWith('--- ')) continue;
      if (l.startsWith('index ') || l.startsWith('new file') || l.startsWith('deleted file') || l.startsWith('old mode') || l.startsWith('new mode') || l.startsWith('similarity ') || l.startsWith('rename ') || l.startsWith('copy ')) continue;
      if (!inBody) continue;
      if (l.startsWith('\\')) continue;
      if (l.startsWith('@@') || l.startsWith('+') || l.startsWith('-') || l.startsWith(' ') || l === '') {
        body.push(l === '' ? ' ' : l);
      }
    }
    if (path) files[path] = { lines: body, binary };
  }
  return files;
}

const builtArcs = [];
for (const arc of META.arcs) {
  const prs = [];
  for (const entry of arc.prs) {
    const [num, shortTitle] = entry;
    process.stderr.write(`fetching #${num}\n`);
    const meta = JSON.parse(sh(`gh pr view ${num}${repoFlag} --json number,title,body,additions,deletions,mergedAt,url,files`));
    const diffText = sh(`gh pr diff ${num}${repoFlag}`);
    const parsed = parseDiff(diffText);
    const files = meta.files.map((f) => ({
      path: f.path,
      additions: f.additions,
      deletions: f.deletions,
      binary: parsed[f.path]?.binary ?? (f.additions === 0 && f.deletions === 0),
      lines: parsed[f.path]?.lines ?? [],
    }));
    prs.push({ number: meta.number, title: meta.title, shortTitle: shortTitle || meta.title, body: meta.body, additions: meta.additions, deletions: meta.deletions, mergedAt: meta.mergedAt, url: meta.url, files });
  }
  builtArcs.push({ title: arc.title, icon: arc.icon || 'circle', desc: arc.desc || '', story: arc.story || arc.title, why: arc.why || '', what: arc.what || [], impact: arc.impact || [], prs });
}

const DATA = {
  title: META.title, stats: META.stats || [],
  overviewTitle: META.overviewTitle || '', overviewLede: META.overviewLede || '',
  closing: META.closing || { title: '', stats: [], takeaways: [] }, arcs: builtArcs,
};

const template = readFileSync(join(DIR, 'template.html'), 'utf8');
// Escape "<" so diff content containing </script>, <!--, etc. cannot break out of the inline <script>,
// plus the two raw separators that are illegal inside JS string literals.
const json = JSON.stringify(DATA)
  .replace(/</g, '\\u003c')
  .replace(new RegExp(String.fromCharCode(0x2028), 'g'), '\\u2028')
  .replace(new RegExp(String.fromCharCode(0x2029), 'g'), '\\u2029');
const out = template.replace(/\/\*__DATA__\*\/[\s\S]*?\/\*__END__\*\//, () => '/*__DATA__*/ ' + json + ' /*__END__*/');
writeFileSync(outPath, out);
process.stderr.write(`\nwrote ${outPath} (${(out.length / 1024).toFixed(0)} kB)\n`);
