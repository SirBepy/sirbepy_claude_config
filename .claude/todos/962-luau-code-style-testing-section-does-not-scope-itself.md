<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=7, reconfirm-count=1, content-hash=aa5c92e5 -->
<!-- duplicate-checked: this is about scoping luau.md's testing section to in-Studio packages, not about the testing floor in CLAUDE.md or any /test skill behaviour -->
# luau.md's testing section reads as binding on lune-native build tooling

**Type:** skill-improvement
**Origin:** ai

## Goal

Scope the "Testing Roblox / Luau Code" section in `~/.claude/code-style/luau.md` to in-Studio
Roblox runtime packages, so a `/code-check` convention pass stops reading it as a rule that binds
lune-native build tooling.

## Context

Surfaced 2026-09-05 by the independent `/code-check` reviewer on
`roblox-trend-pipeline`'s `a76c24b..e80e984` range, as an unwritten-rule observation. Recorded
here rather than in that project, since the file to change is global.

That section prescribes `jest-lua` plus `run-in-roblox`, Studio-driven execution, and
`tests/<package>/<Module>.spec.luau` naming. `roblox-trend-pipeline`'s `rbxl-gen` is a lune CLI
build tool: its suite is `tests/rbxl-gen/test_*.luau` run headless via
`lune run tests/rbxl-gen/run`, with no Studio and no jest-lua anywhere. Neither convention applies,
and neither should.

The reviewer correctly declined to file it as a code breach, on the grounds that a rule only binds
files in the stack it targets. But nothing in `luau.md` states that boundary, so the judgement had
to be made from scratch. It will have to be made from scratch again on every future review of that
repo, and a less careful reviewer files it as a `BLOCKER:` convention finding instead, since
`/code-check` Step 4 tells it to judge against whatever `~/.claude/code-style/<stack>.md` says.

Luau now has two genuinely different execution contexts, and the file was written when it
effectively had one.

## Approach

1. Read `~/.claude/code-style/luau.md` in full and find the testing section's actual heading.
2. Add one scoping sentence at the top of that section naming what it governs: code that runs
   inside Roblox (Studio, a live place, a runtime package), and what it does not: lune-native
   tooling that runs headless on the developer's machine.
3. Decide whether a short second paragraph is warranted for the lune-native case, or whether
   "follow the package's existing harness" is enough. Prefer the smaller edit; the point is to stop
   a false positive, not to write a second testing doctrine on speculation.
4. Check whether any other section of `luau.md` has the same implicit-Studio assumption while you
   are in the file, and scope those the same way if so.

Rejected: leaving it and relying on each reviewer to work the boundary out. That is what happened
here, and it worked only because the reviewer was careful. A rule that needs judgement to know
whether it applies is the rule most likely to be misapplied.

## Acceptance

- The testing section names the context it governs in its own text.
- A reader can tell from the section alone whether it binds a lune CLI package.
- `python ci/run_all.py` passes.
- No other `code-style/*.md` file is touched.
