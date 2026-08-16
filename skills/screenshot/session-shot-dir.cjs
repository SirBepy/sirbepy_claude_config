// Shared helper: resolves and creates this session's throwaway-screenshot subfolder, so callers
// never hand-build the <pid>-<start-ticks> id/path themselves (todo 287 - a hand-named folder
// left files `/close` could never find, because ownership only worked if the writer remembered
// the rule). Wraps close/rename-session.ps1 -GetId (Windows) / rename-session.sh --get-id (POSIX).
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CLAUDE_ROOT = path.join(os.homedir(), '.claude');

// -GetId now refuses (non-zero exit) when it can't resolve a reliable id - e.g. called from a
// detached subagent process (todo 346). Re-throw with the doctrine pointer front and center so a
// caller that only shows e.message doesn't just see a raw "Command failed" stack.
function getSessionId() {
  try {
    if (process.platform === 'win32') {
      const script = path.join(CLAUDE_ROOT, 'skills', 'close', 'rename-session.ps1');
      return execFileSync('powershell', ['-NoProfile', '-File', script, '-GetId'], { encoding: 'utf8' }).trim();
    }
    const script = path.join(CLAUDE_ROOT, 'skills', 'close', 'rename-session.sh');
    return execFileSync(script, ['--get-id'], { encoding: 'utf8' }).trim();
  } catch (e) {
    const detail = (e.stderr || e.message || '').toString().trim();
    throw new Error(`Could not resolve a reliable session id - pass one in instead of re-deriving it here. ${detail}`);
  }
}

// cwd defaults to the project root (process.cwd()), matching every other .for_bepy/ convention.
function getSessionShotDir(cwd = process.cwd()) {
  const id = getSessionId();
  const dir = path.join(cwd, '.for_bepy', 'screenshots', id);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

if (require.main === module) {
  try {
    process.stdout.write(getSessionShotDir());
  } catch (e) {
    console.error('Could not resolve session screenshot dir:', e.message);
    process.exit(1);
  }
}

module.exports = { getSessionShotDir, getSessionId };
