"""Self-test for memory-trigger.py / _memory_triggers.py (todo 1153).

Run directly: python hooks/test_memory_trigger.py
Exits 0 on all-pass, 1 on any failure. Every case runs against a scratch
corpus and scratch state dir; nothing under the real memory dirs is read.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
mt = _testlib.load_module("memory_triggers_lib", _HOOKS_DIR / "_memory_triggers.py")
_HOOK_PATH = _HOOKS_DIR / "memory-trigger.py"


def memory(name, triggers_block, body="Do the thing.", extra=""):
    return f"---\nname: {name}\ndescription: test memory {name}\n{triggers_block}{extra}metadata:\n  type: feedback\n---\n{body}\n"


class World:
    """A scratch corpus (root/proj/memory/*.md), state dir and repo."""

    def __init__(self, tmp):
        self.tmp = Path(tmp)
        self.root = self.tmp / "projects"
        self.mem = self.root / "projA" / "memory"
        self.mem.mkdir(parents=True)
        self.repo = self.tmp / "repos" / "my-repo"
        (self.repo / ".git").mkdir(parents=True)
        (self.repo / "src").mkdir()
        os.environ[mt.STATE_ENV] = str(self.tmp / "state")
        os.environ[mt.RECHECK_ENV] = "0"
        self.roots = [str(self.root)]
        self.n = 0

    def add(self, filename, text):
        p = self.mem / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        # Corpus fingerprint uses mtimes: make sure each write is a distinct instant.
        self.n += 1
        t = time.time() + self.n
        os.utime(p, (t, t))
        return p

    def call(self, tool, tool_input, session="s1", cwd=None):
        payload = {"tool_name": tool, "tool_input": tool_input, "session_id": session, "cwd": cwd or str(self.tmp)}
        return mt.run_hook(payload, roots=self.roots, today="2026-11-07")


def context_of(result):
    code, out, err = result
    if not out:
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


results = []


def case(label, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    results.append((label, ok))


def run_cases(w):
    # --- parsing and globs
    fm = mt.parse_frontmatter(["name: n", "triggers:", "  paths:", '    - "a/**/b.ts"', "    - c.md",
                               "  skills: [x, 'y z']", "  repos: r1", "once: true"])
    case("parser: block list, inline list, scalar repo, once",
         fm["triggers"] == {"paths": ["a/**/b.ts", "c.md"], "skills": ["x", "y z"], "repos": ["r1"]} and fm["once"] is True)
    import re
    rx = mt.glob_to_regex("auth/*.ts")
    case("glob: tail match across a Windows path, case-insensitive",
         bool(re.match(rx, mt._norm_path(r"C:\Repo\SRC\Auth\login.ts"))))
    case("glob: * does not cross directories", not re.match(rx, mt._norm_path("x/auth/sub/login.ts")))
    case("glob: ** crosses directories",
         bool(re.match(mt.glob_to_regex("**/clockify/**"), mt._norm_path("C:/a/b/clockify/c/d.js"))))

    # --- path, skill, repo matching
    w.add("clockify.md", memory("clockify", "triggers:\n  paths: [\"**/clockify-reconciliator/**\"]\n", "Meal gap rule: subtract 45 minutes."))
    w.add("skillmem.md", memory("skillmem", "triggers:\n  skills: [ticket]\n", "Ticket rule."))
    w.add("repomem.md", memory("repomem", "triggers:\n  repos: [my-repo]\n", "Repo rule."))
    w.add("plain.md", memory("plain", "", "No triggers here."))
    w.add("super.md", memory("super", "triggers:\n  skills: [ticket]\n", "Superseded.", extra="superseded_by: skillmem\n"))
    (w.mem / "archive").mkdir()
    w.add("archive/old.md", memory("old", "triggers:\n  skills: [ticket]\n", "Archived."))
    w.add("MEMORY.md", "- [x](x.md) - index, never a memory\n")

    r = w.call("Read", {"file_path": r"C:\Users\tecno\.claude\skills\clockify-reconciliator\SKILL.md"}, "p1")
    case("path glob fires on Read and injects the body", "Meal gap rule" in context_of(r) and r[0] == 0)
    r = w.call("Edit", {"file_path": "C:/x/clockify-reconciliator/a.js"}, "p1")
    case("once per session: same memory is not injected twice", r == (0, "", ""))
    r = w.call("Read", {"file_path": "C:/x/clockify-reconciliator/a.js"}, "p2")
    case("a different session gets it again", "Meal gap rule" in context_of(r))
    r = w.call("Read", {"file_path": "C:/x/unrelated/a.js"}, "p3")
    case("an unrelated path injects nothing", r == (0, "", ""))

    r = w.call("Skill", {"skill": "ticket"}, "k1")
    ctx = context_of(r)
    case("skill trigger fires on the Skill tool", "Ticket rule" in ctx)
    case("superseded and archived memories never fire", "Superseded" not in ctx and "Archived" not in ctx)
    r = w.call("Skill", {"skill": "anthropic-skills:ticket"}, "k2")
    case("plugin-prefixed skill name matches by its last part", "Ticket rule" in context_of(r))

    r = w.call("Read", {"file_path": "C:/x/y.txt"}, "r1", cwd=str(w.repo / "src"))
    case("repo trigger fires from a subdirectory of the repo", "Repo rule" in context_of(r))
    r = w.call("Read", {"file_path": "C:/x/y.txt"}, "r2", cwd=str(w.tmp))
    case("repo trigger stays quiet outside the repo", "Repo rule" not in context_of(r))
    r = w.call("Bash", {"command": "ls"}, "r3", cwd=str(w.repo))
    case("tools outside the covered set are ignored", r == (0, "", ""))

    # --- once: true retirement
    p = w.add("onceonly.md", memory("onceonly", "triggers:\n  paths: [\"special/*.cfg\"]\n", "Next time you touch this, bump the version.", extra="once: true\n"))
    r = w.call("Edit", {"file_path": "C:/p/special/a.cfg"}, "o1")
    case("once-memory fires", "bump the version" in context_of(r))
    case("once-memory is stamped fired: in its frontmatter", "fired: 2026-11-07" in p.read_text(encoding="utf-8"))
    r = w.call("Edit", {"file_path": "C:/p/special/a.cfg"}, "o2")
    case("a retired once-memory does not fire in a new session", "bump the version" not in context_of(r))
    case("once-memory body is untouched by the stamp", "Next time you touch this, bump the version." in p.read_text(encoding="utf-8"))

    # --- stale-table rebuild
    table_file = Path(mt.table_path())
    before = table_file.read_bytes()
    w.call("Read", {"file_path": "C:/x/y.txt"}, "t1")
    case("unchanged corpus leaves the table as it was", table_file.read_bytes() == before)
    w.add("late.md", memory("late", "triggers:\n  paths: [\"late/**\"]\n", "Late arrival."))
    r = w.call("Read", {"file_path": "C:/x/late/f.txt"}, "t2")
    case("a memory added after the table was built is picked up", "Late arrival" in context_of(r))
    w.add("late.md", memory("late", "triggers:\n  paths: [\"later/**\"]\n", "Late arrival, edited."))
    r = w.call("Read", {"file_path": "C:/x/later/f.txt"}, "t3")
    case("an edited memory (newer mtime) is re-read", "edited" in context_of(r))

    # --- incremental rebuild and the recheck window
    parsed = []
    real_read = mt.read_frontmatter
    mt.read_frontmatter = lambda path: (parsed.append(os.path.basename(path)), real_read(path))[1]
    try:
        w.add("late.md", memory("late", "triggers:\n  paths: [\"latest/**\"]\n", "Late arrival, edited again."))
        w.call("Read", {"file_path": "C:/x/y.txt"}, "t4")
    finally:
        mt.read_frontmatter = real_read
    case("a rebuild reparses only the file whose mtime moved", parsed == ["late.md"])
    os.environ[mt.RECHECK_ENV] = "3600"
    w.add("windowed.md", memory("windowed", "triggers:\n  paths: [\"windowed/**\"]\n", "Inside the window."))
    r = w.call("Read", {"file_path": "C:/x/windowed/f.txt"}, "t5")
    case("inside the recheck window the corpus walk is skipped", context_of(r) == "")
    os.environ[mt.RECHECK_ENV] = "0"
    r = w.call("Read", {"file_path": "C:/x/windowed/f.txt"}, "t6")
    case("once the window is off the new memory is seen", "Inside the window" in context_of(r))

    # --- Agent dispatch
    w.add("agentmem.md", memory("agentmem", "triggers:\n  skills: [playwright-wall]\n", "Playwright needs the profile flag."))
    r = w.call("Agent", {"prompt": "Run /playwright-wall checks on the site", "description": "x"}, "a1")
    case("Agent dispatch is held once with the memory text", r[0] == 2 and "Playwright needs the profile flag" in r[2] and "Re-dispatch" in r[2])
    r = w.call("Agent", {"prompt": "Run /playwright-wall checks on the site", "description": "x"}, "a1")
    case("the retried Agent dispatch is not held again", r == (0, "", ""))
    r = w.call("Agent", {"prompt": "Summarise the README", "description": "x"}, "a2")
    case("an Agent prompt that mentions nothing triggered passes", r == (0, "", ""))

    # --- pc-review item 12: an Agent prompt matches a skill only as a /name token, never as a bare word
    r = w.call("Agent", {"prompt": "Run playwright-wall checks on the site", "description": "x"}, "a3")
    case("a bare skill word in an Agent prompt does not fire", r == (0, "", ""))
    r = w.call("Agent", {"prompt": "Use the anthropic-skills:playwright-wall flow", "description": "x"}, "a3b")
    case("a plugin-prefixed bare word in an Agent prompt does not fire", r == (0, "", ""))
    r = w.call("Agent", {"prompt": "Run /anthropic-skills:playwright-wall on the site", "description": "x"}, "a4")
    case("a plugin-prefixed /name token in an Agent prompt fires", r[0] == 2 and "Playwright needs the profile flag" in r[2])
    for i, (label, prompt) in enumerate([
        ("a path segment named like the skill", "Read skills/playwright-wall/SKILL.md and C:/x/playwright-wall/a.md"),
        ("a Windows path segment named like the skill", "Open C:\\skills\\playwright-wall\\SKILL.md"),
        ("a longer skill-like word after the slash", "Run /playwright-wall-extra now"),
        ("a URL ending in the skill name", "Fetch http://host/x/playwright-wall"),
    ]):
        r = w.call("Agent", {"prompt": prompt, "description": "x"}, f"a5{i}")
        case(f"Agent prompt with {label} does not fire", r == (0, "", ""))
    w.add("commitmem.md", memory("commitmem", "triggers:\n  skills: [commit]\n", "Commit memory body.", extra="once: true\n"))
    r = w.call("Agent", {"prompt": "Fix the parser, then commit your changes and git commit -m x.", "description": "commit work"}, "a6")
    case("the plain word commit in an Agent prompt does not fire a commit-skill memory", "Commit memory body" not in r[2] and r[1] == "")
    case("and does not retire its once-memory", "fired:" not in (w.mem / "commitmem.md").read_text(encoding="utf-8"))
    r = w.call("Skill", {"skill": "commit"}, "a7")
    case("the Skill tool still fires the commit-skill memory", "Commit memory body" in context_of(r))

    # --- pc-review item 12: a comma inside braces or quotes is part of the glob, not a list separator
    fm = mt.parse_frontmatter(["triggers:", "  paths: [\"src/{a,b}/*.ts\", c/{d,e}.md, 'x,y.txt']"])
    case("parser: commas inside braces and quotes stay in one glob",
         fm["triggers"]["paths"] == ["src/{a,b}/*.ts", "c/{d,e}.md", "x,y.txt"])
    rx = mt.glob_to_regex("src/{a,b}/*.ts")
    case("glob: braces match each alternative", bool(re.match(rx, "c:/p/src/a/z.ts")) and bool(re.match(rx, "c:/p/src/b/z.ts")))
    case("glob: braces reject a non-alternative", not re.match(rx, "c:/p/src/c/z.ts"))
    case("glob: the literal brace text no longer matches", not re.match(rx, "c:/p/src/{a,b}/z.ts"))

    # --- a memory cut by the size cap has not been shown, so it is neither fired nor retired
    bulk = [w.add(f"bulk{i}.md", memory(f"bulk{i}", "triggers:\n  paths: [\"bulk/**\"]\n", f"BULK{i} " + "x" * 1900, extra="once: true\n")) for i in range(3)]
    r = w.call("Read", {"file_path": "C:/x/bulk/f.txt"}, "c1")
    shown = [i for i in range(3) if f"BULK{i} " in context_of(r)]
    stamped = [i for i, p in enumerate(bulk) if "fired:" in p.read_text(encoding="utf-8")]
    case("size cap: only memories actually shown are retired", len(shown) == 2 and sorted(stamped) == sorted(shown))
    r = w.call("Read", {"file_path": "C:/x/bulk/f.txt"}, "c2")
    left = [i for i in range(3) if i not in shown][0]
    case("size cap: the memory that was cut still reaches a later call", f"BULK{left} " in context_of(r))

    # --- line endings survive the once-retirement stamp
    crlf = w.mem / "crlf.md"
    crlf.write_bytes(b"---\r\nname: crlf\r\ntriggers:\r\n  paths: [\"crlf/**\"]\r\nonce: true\r\n---\r\nCRLF body.\r\n")
    t = time.time() + 500
    os.utime(crlf, (t, t))
    w.call("Read", {"file_path": "C:/x/crlf/f.txt"}, "e1")
    raw = crlf.read_bytes()
    case("retire_once keeps CRLF files CRLF with no doubled CR", b"fired: 2026-11-07\r\n" in raw and b"\r\r" not in raw)

    # --- a hold needs a persisted fired set, or the retry would be held forever
    w.add("nosession.md", memory("nosession", "triggers:\n  skills: [nosession-skill]\n", "No session id."))
    r = w.call("Agent", {"prompt": "use /nosession-skill here", "description": "x"}, "")
    case("Agent hold is skipped when the fired set cannot be saved", r[0] == 0 and "No session id" in json.loads(r[1])["hookSpecificOutput"]["additionalContext"])

    # --- degenerate inputs
    case("non-dict tool_input is ignored", mt.run_hook({"tool_name": "Read", "tool_input": "oops"}, roots=w.roots) == (0, "", ""))
    bad = w.add("bad.md", "---\nname: [unterminated\n")
    r = w.call("Read", {"file_path": "C:/x/y.txt"}, "b1")
    case("a malformed memory file does not break matching", r[0] == 0)


def run_subprocess_cases(w):
    env = dict(os.environ)
    env[mt.ROOTS_ENV] = str(w.root)
    env[mt.STATE_ENV] = str(w.tmp / "state-sub")
    payload = {"tool_name": "Read", "tool_input": {"file_path": "C:/x/clockify-reconciliator/z.md"}, "session_id": "sub1", "cwd": str(w.tmp)}
    proc = subprocess.run([sys.executable, str(_HOOK_PATH)], input=json.dumps(payload), capture_output=True, text=True, env=env)
    ok = proc.returncode == 0 and "Meal gap rule" in json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    case("process: Read hit prints additionalContext JSON, exit 0", ok)
    proc = subprocess.run([sys.executable, str(_HOOK_PATH)], input="not json", capture_output=True, text=True, env=env)
    case("process: garbage stdin fails open", proc.returncode == 0)
    payload["tool_name"], payload["tool_input"] = "Agent", {"prompt": "/playwright-wall", "description": "d"}
    payload["session_id"] = "sub2"
    proc = subprocess.run([sys.executable, str(_HOOK_PATH)], input=json.dumps(payload), capture_output=True, text=True, env=env)
    case("process: Agent hold is exit 2 with the memory on stderr", proc.returncode == 2 and "Playwright needs the profile flag" in proc.stderr)


def run() -> int:
    saved_state = os.environ.get(mt.STATE_ENV)
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        run_cases(w)
        run_subprocess_cases(w)
    if saved_state is None:
        os.environ.pop(mt.STATE_ENV, None)
    else:
        os.environ[mt.STATE_ENV] = saved_state
    return _testlib.summarize([label for label, ok in results if not ok])


if __name__ == "__main__":
    sys.exit(run())
