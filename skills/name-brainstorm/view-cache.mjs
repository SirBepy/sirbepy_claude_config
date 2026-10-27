// Reads a check-availability.mjs --resume cache and prints one compact line per name.
// Usage: node view-cache.mjs <cache.json> list a,b,c   - statuses for the named names
//        node view-cache.mjs <cache.json> comfree        - every name with .com free
//        node view-cache.mjs <cache.json> aifree         - names with .ai free but .com taken
// Letters: F = FREE, T = TAKEN, ? = not checked (never looked up, or UNKNOWN). A name checked with
// --skip hr shows hr=?, which means "not looked up", not "free".
import fs from 'node:fs';

const [cachePath, mode, arg] = process.argv.slice(2);
if (!cachePath || !mode) {
  console.error('Usage: node view-cache.mjs <cache.json> list <a,b,c> | comfree | aifree');
  process.exit(1);
}
const cache = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
const names = new Set(Object.keys(cache).map((k) => k.split(':')[1]));
const status = (kind, name) => (cache[`${kind}:${name}`]?.status ?? '?')[0];
const kinds = ['com', 'ai', 'io', 'app', 'dev', 'eu', 'hr', 'npm', 'github'];
const row = (name) => `${name.padEnd(12)} ${kinds.map((k) => `${k}=${status(k, name)}`).join(' ')}`;

if (mode === 'list') {
  for (const name of (arg ?? '').split(',').filter(Boolean)) console.log(row(name));
} else if (mode === 'comfree') {
  const hits = [...names].filter((n) => status('com', n) === 'F').sort();
  console.log(`${hits.length} of ${names.size} with .com free`);
  for (const n of hits) console.log(row(n));
} else if (mode === 'aifree') {
  const hits = [...names].filter((n) => status('ai', n) === 'F' && status('com', n) !== 'F').sort();
  console.log(`${hits.length} with .ai free but .com taken`);
  console.log(hits.join(' '));
} else {
  console.error(`unknown mode ${mode}`);
  process.exit(1);
}
