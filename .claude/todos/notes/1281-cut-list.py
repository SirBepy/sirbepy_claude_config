# Dry-run of todo 1281's CLAUDE.md cut list: applies every cut to a COPY in memory and prints
# line number, action, destination, quoted span and tokens saved. Writes nothing. Anchors are
# exact strings from CLAUDE.md as of 2026-11-07 (after todos 1155/1270/1272/1296 landed); if the
# file changed since, an assertion names the item whose anchor no longer matches.
# Run from anywhere: python -I 1281-cut-list.py
import re, sys
from pathlib import Path
src = (Path(__file__).resolve().parents[3] / 'CLAUDE.md').read_text(encoding='utf-8')
s = src
lines0 = src.split('\n')

def line_of(span_start):
    return src[:src.index(span_start)].count('\n') + 1

# (id, action, dest, start_anchor, end_anchor, replacement)
# span = from start_anchor through end_anchor inclusive, must be unique and non-overlapping.
I = [
 ("01","cut (illustration)","-","Applies even to tasks that look like mechanical pattern replication","or only in one app state?).",""),
 ("02","cut (story already in refs/incidents.md)","incidents.md","A product-looking question is usually a FE call","main context should hold the verdict only.",""),
 ("03","condense","-","chips there, so hand-written tags","redundant noise.","chips there."),
 ("04","condense 5 tag bullets to 1","-","  - `[UX]` - visual, layout","  - `[TOOLING]` - dev tooling, linting, code style, naming","  - `[UX]` taste dominates (skip the axes, still recommend); `[ARCH]`/`[SEC]` Claude's input is load-bearing; `[DATA]` schema; `[TOOLING]` tooling, style, naming"),
 ("05","condense (ref already holds the full ruleset)","copy-paste-format.md"," Core: everything Joe should copy goes in a BLOCKQUOTE","message length limits."," Core: copyable text goes in a BLOCKQUOTE, except backslashes or multi-line runnable blocks (fenced code)."),
 ("06","condense","incidents.md"," Not \"usually\", not \"unless the thread is Croatian\".","(that line governs only the copyable block)."," Only the copyable draft takes the recipient's language, even for a Croatian thread; this overrides `refs/copy-paste-format.md`'s \"match Joe's language\" line for Claude-to-Joe text."),
 ("07","condense","-","(GitHub/git credential picker, UAC, auth/login popups, browser permission dialogs, keychain, MFA, any external dialog), proactively","Never let Joe wonder who triggered a popup.","(credential picker, UAC, auth popup, any external dialog), tell Joe immediately that it came from Claude and name the exact command/action."),
 ("08","condense (snippets/terse-replies.md already says it)","-"," No play-by-play (\"Now let me","or question.",": no play-by-play, batch independent calls, one tight summary at the end; surface mid-task only a real decision, blocker, or question."),
 ("09","condense","-"," It covers when to commit without asking, and when to fold","just run `/commit`.",". Never ask \"should I commit this?\": run `/commit`."),
 ("10","condense (refs/builder-preamble.md holds the exact lines, dispatch-preamble-guard.py enforces them)","builder-preamble.md"," Every dispatch prompt MUST include a staging line:","background subagents: `refs/process-hygiene.md`."," Every dispatch prompt MUST carry the staging line from `refs/builder-preamble.md` (`hooks/dispatch-preamble-guard.py` checks it). A subagent's raw `git commit` stays hook-blocked."),
 ("11","condense (hook-enforced)","-","- A global `PreToolUse` hook (`~/.claude/hooks/gh-account-switch.sh`)","separate, already-correct system.","- `hooks/gh-account-switch.sh` switches `gh`'s account to match the repo's `origin` (mapping in its header). On \"Could not resolve to a Repository\" the hook didn't fire (wrong cwd): switch to the mapped account and retry, do NOT assume the account was deleted."),
 ("12","condense (guard + ref carry it)","shell-io-gotchas.md"," Windows PowerShell 5.1 prepends a UTF-8 BOM","a `python`/`node` heredoc opening it stay allowed."," PowerShell 5.1 prepends a UTF-8 BOM that breaks most parsers. The ban covers the mechanism, not just the encoding, and overrides any harness preamble telling Claude to write via shell; `cat`/`sed`/`grep` reads and a `python`/`node` heredoc opening it stay allowed (`hooks/shell-content-write-guard.py` blocks it but fails open)."),
 ("13","condense","-","- The same encoding layer corrupts the inbound direction too:","examples and failure: `refs/shell-io-gotchas.md`.","- Never pipe file content INTO a native command (`Get-Content | exe`): use Bash `<`. Details: `refs/shell-io-gotchas.md`."),
 ("14","move to a new ref","NEW refs/package-safety.md","- The advisory-DB check must run against the ACTUAL RESOLVED dependency tree","name-keyed lookup alone.\n","- Run the advisory check on the ACTUAL RESOLVED tree (install, then `npm audit --json` / `cargo audit`), not a name lookup of the top-level package; detail in `refs/package-safety.md`.\n"),
 ("15","merge two bullets","-","- A subagent is required for research on anything load-bearing or crypto/network.\n- Otherwise prefer one; a single obvious package can be an inline web search.","inline web search.","- Research on anything load-bearing or crypto/network needs a subagent; a single obvious package can be an inline web search."),
 ("16","move to refs/process-hygiene.md (already has the commands, lines 25-37)","process-hygiene.md"," After running test/build/dev commands, check with `Get-CimInstance","before claiming done."," Run the orphan check in `refs/process-hygiene.md` after test/build/dev commands and kill leftovers before claiming done."),
 ("17","move to refs/process-hygiene.md (flags already at line 42-52)","process-hygiene.md"," turbo `--concurrency=5`; vitest `maxWorkers: 5`","(plain `pnpm install` takes no concurrency flag)."," flags per tool in `refs/process-hygiene.md`."),
 ("18","cut","-"," Keep it in the code, not just the commit: the next reader, human or AI, reads the file cold.","",""),
 ("19","cut (example)","-"," (`74px rail, 36px avatar, so 7px centres it`)","",""),
 ("20","cut","-"," Same rule in every repo; no numeric cap.","",""),
 ("21","cut (admission, not a rule)","-"," Honest limitation: nothing enforces this","has no mechanical catch.",""),
 ("22","condense","-"," - hedging the noun doesn't hedge a trailing \"so Y happens\" clause - the whole sentence needs the label.","needs the label.","; the label covers the whole sentence."),
 ("23","condense","-"," Describing what a skill, command, or third-party artifact will do counts too:","summaries drift."," That includes what a skill or third-party artifact does: read its own `SKILL.md` or raw source, never a summary."),
 ("24","condense (hook-enforced half)","outbound-verify.md","Tickets and PRs Claude posts itself are hook-enforced:","which has no tool call to hook.","Tickets and PRs Claude posts are hook-enforced (`refs/outbound-verify.md`); this bullet covers the chat half."),
 ("25","cut","-"," Not a licence to skip on judgment alone - only an explicit dev instruction does.","",""),
 ("26","condense (duplicates /commit Push pipeline and push-gate.py)","-","Every commit runs `/test`, every push runs `/code-check` + `/e2e` (a repo with no e2e suite notes \"no suite\"), and `hooks/push-gate.py` blocks the push until that is done. The full ordered step list lives only in `/commit`'s \"Push pipeline\" section.","\"Push pipeline\" section.","Every commit runs `/test`, every push the pipeline in `/commit`'s \"Push pipeline\" section (`hooks/push-gate.py` blocks a push until it is done)."),
 ("27","cut whole line (restates the line above it)","-","- `/test` means the normal (fast) tests;","Both stay fast-only.\n",""),
 ("28","condense","-","Phosphor via CDN (`<script","Browse: https://phosphoricons.com","Use the web CDN or `@phosphor-icons/react`."),
 ("29","cut","-",": focus can silently land on the wrong window and capture unrelated private content.","",": focus can land on the wrong window."),
 ("30","condense (todo ids are history)","-"," (`<pid>-<procStart-ticks>`, resolved from","(todo 324).",", never hand-rolled)."),
 ("31","cut (contract file covers it)","close/ai-todos-format.md","Written by `/close`, `/create-todo`, `/code-check`, autopilot; ordered by `/plan-todos`; executed via `/pickup`, `/auto-do-todos`, or Joe naming an id - ","naming an id - ",""),
 ("32","condense","-"," Write it there and move on; do not queue it locally \"for later\". The path is repo-relative","see `close/ai-todos-format.md`."," Never queue it locally \"for later\"."),
 ("33","cut (history)","-"," ai_todos moved OUT of here to `.claude/todos/` on 2026-07-15;","unmigrated legacy.",""),
 ("34","cut (example list)","-"," (Riverpod / context / useState / module-scope)","",""),
 ("35","cut (ref has it)","global-knowledge-vault.md"," The vault is shared across 3+ concurrent sessions with no file locking","never whole-file.",""),
 ("36","move to refs/memory-rubric.md","memory-rubric.md","is harness-internal advisory, not a rule to obey - it re-fires","or later run `/cleanup-memory`.","is advisory: surface it, keep working, never delete entries mid-task."),
 ("37","cut","-",", even an ad-hoc one with no skill in the loop","",""),
 ("38","cut","-"," A single-fact lookup (one version check, one typosquat check) stays inline.","",""),
 ("39","cut (restates the heading)","-"," A well-written dispatch prompt (precise spec, file paths, constraints, report-back shape) determines subagent quality.","",""),
 ("40","condense","delegation-doctrine.md","The rules above govern ordinary dispatches. A pure ORCHESTRATOR session","not by default.","A pure ORCHESTRATOR session (`/delegate`, `/autopilot`) follows `~/.claude/refs/delegation-doctrine.md`, which defers to this section for model tier."),
 ("41","cut","-","Replaces the caveman plugin (uninstalled) - ","",""),
 ("42","cut (example)","-"," E.g. \"Claude will write them to Clockify\", \"Claude will POST the new entries\", not \"I'll write them\" or \"you'll write them\".","",""),
 ("43","cut","-"," (a settings.json edit, a newly installed skill or hook)","",""),
]
rows = []
total = 0
cur = s
for (i, act, dest, a, b, rep) in I:
    # exact span: whole text of 'a' alone when b is empty
    if b == "":
        old = a
        assert cur.count(old) == 1, (i, 'anchor count', cur.count(old), a[:50])
        st = cur.index(old); en = st + len(old)
    else:
        assert cur.count(a) >= 1, (i, 'start missing', a[:50])
        st = cur.index(a)
        assert cur.count(a) == 1, (i, 'start not unique', a[:50])
        e = cur.index(b, st)
        en = e + len(b)
    old = cur[st:en]
    ln = src[:src.index(a)].count('\n') + 1
    saved_chars = len(old) - len(rep)
    cur = cur[:st] + rep + cur[en:]
    rows.append((i, ln, act, dest, old, rep, saved_chars))
    total += saved_chars
tok0 = -(-len(src) // 4)
tok1 = -(-len(cur) // 4)
print("chars", len(src), "->", len(cur), "tokens", tok0, "->", tok1, "saved", tok0 - tok1, "ceiling 6558 headroom", 6558 - tok1)
for (i, ln, act, dest, old, rep, sc) in rows:
    short = old.replace('\n', ' / ')
    if len(short) > 90:
        short = short[:55] + ' ... ' + short[-30:]
    short = short.replace('|', '/').replace('…', '...')
    print(f"| {i} | {ln} | {act} | {dest} | `{short}` | {round(sc/4)} |")
