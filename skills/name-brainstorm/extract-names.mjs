// Merges the idea files of a naming round into one name list for check-availability.mjs.
// Usage: node extract-names.mjs <ideas-dir> <out.txt> [--exclude a.txt,b.txt]
// Idea files hold lines `Name | label | ...`; only the first column counts. Keeps one-word names
// of 4-12 ASCII letters (diacritics stripped), lowercased, deduped, minus the exclude lists.
import fs from 'node:fs';

const [dir, outPath, ...rest] = process.argv.slice(2);
if (!dir || !outPath) {
  console.error('Usage: node extract-names.mjs <ideas-dir> <out.txt> [--exclude a.txt,b.txt]');
  process.exit(1);
}
const exIdx = rest.indexOf('--exclude');
const excludeFiles = exIdx >= 0 && rest[exIdx + 1] ? rest[exIdx + 1].split(',') : [];

const exclude = new Set();
for (const f of excludeFiles) {
  if (!fs.existsSync(f)) {
    console.error(`exclude file not found: ${f}`);
    process.exit(1);
  }
  for (const line of fs.readFileSync(f, 'utf8').split('\n')) {
    const w = line.trim().toLowerCase();
    if (w && !w.startsWith('#')) exclude.add(w);
  }
}

const found = new Set();
for (const file of fs.readdirSync(dir)) {
  if (!file.endsWith('.md')) continue;
  for (const line of fs.readFileSync(`${dir}/${file}`, 'utf8').split('\n')) {
    // Header, TOP: and prose lines carry no ` | `; comma lists are accepted only when the line has no colon.
    if (line.startsWith('#') || line.startsWith('TOP:')) continue;
    const head = line.includes(' | ') ? line.split(' | ')[0] : line.includes(',') && !line.includes(':') ? line : '';
    for (const part of head.split(',')) {
      const word = part.replace(/\(.*?\)/g, '').trim();
      if (!word || /\s/.test(word)) continue;
      const ascii = word.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'dj').toLowerCase();
      if (/^[a-z]{4,12}$/.test(ascii)) found.add(ascii);
    }
  }
}

const names = [...found].filter((n) => !exclude.has(n)).sort();
fs.writeFileSync(outPath, names.join('\n') + '\n');
console.log(`${found.size} unique, ${found.size - names.length} excluded, ${names.length} written to ${outPath}`);
