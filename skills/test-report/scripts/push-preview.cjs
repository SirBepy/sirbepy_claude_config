// Pushes a report to the Conductor panel. Usage: node push-preview.cjs <out.html> <slug> <title>
const fs = require('fs');

const [file, slug, title] = process.argv.slice(2);
const sessionId = process.env.CLAUDE_CODE_SESSION_ID;
if (!title) { console.error('usage: node push-preview.cjs <out.html> <slug> <title>'); process.exit(2); }
if (!sessionId) { console.error('CLAUDE_CODE_SESSION_ID is not set: run this inside a Conductor chat'); process.exit(2); }

fetch('http://127.0.0.1:27182/hooks/preview', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title, slug, html: fs.readFileSync(file, 'utf8'), source: 'terminal', session_id: sessionId }),
}).then(async (r) => {
  console.log(r.status, (await r.text()).slice(0, 200));
  process.exit(r.ok ? 0 : 1);
}).catch((e) => { console.error(e.message); process.exit(1); });
