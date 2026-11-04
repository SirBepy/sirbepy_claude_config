// Prints on or off for the repo in cwd. A repo is on when its origin is listed in refs/test-report-repos.txt.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

const list = fs.readFileSync(path.join(os.homedir(), '.claude', 'refs', 'test-report-repos.txt'), 'utf8')
  .split(/\r?\n/).map((l) => l.trim().toLowerCase()).filter((l) => l && !l.startsWith('#'));
let origin = '';
try { origin = execSync('git remote get-url origin', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim().toLowerCase(); } catch { /* not a repo, or no origin: off */ }
const slug = origin.replace(/\.git$/, '').replace(/^.*[:/]([^/:]+\/[^/]+)$/, '$1');
console.log(list.includes(slug) ? 'on' : 'off');
