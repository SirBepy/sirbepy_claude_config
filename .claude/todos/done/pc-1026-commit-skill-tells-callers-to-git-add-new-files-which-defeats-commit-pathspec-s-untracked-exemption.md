<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=2f3f90dc -->
<!-- duplicate-checked: 985 is about WHICH markers should count as "shared checkout"; 1025 is about PRINTING the derived ranges when the refusal fires; 989 is about the refuse-then-print-the-answer shape generally. None of the three touch the untracked/`git add` ordering below, which is a contradiction between SKILL.md's prose and the script's own exemption rather than a property of the refusal itself. Do not fold into any of them: fixing this one removes a whole class of refusals that 985/1025 would still have to handle for tracked files. -->
# /commit's "git add new files first" instruction silently defeats commit-pathspec.sh's untracked-file exemption

**Type:** skill-improvement
**Origin:** ai

## Goal

A brand-new file in a commit pathspec stops forcing a needless `--own-range` declaration, so the
untracked exemption `commit-pathspec.sh` already implements is actually reachable by a caller who
followed `SKILL.md`.

## Context

The two halves of the commit skill disagree about when a new file should be staged.

`skills/commit/SKILL.md` step 8 tells the caller to stage it before the commit:

> **Untracked files are the one exception:** a pathspec cannot name a file git doesn't know yet, so
> `git add <new-file> <new-file>` them first, then include them in the same pathspec commit.

`skills/commit/commit-pathspec.sh`'s header grants an exemption keyed on exactly that state:

> A brand-new (untracked) file's auto-derived range stays trusted regardless of session count: it has
> no HEAD baseline, so there is no pre-existing structure for a peer's lines to hide inside.

The script classifies by tracked-ness only, `commit-pathspec.sh:164`:

```sh
if git_c ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then echo live; else echo untracked; fi
```

So `git add`-ing first flips the file from `untracked` to `live`, and the exemption at lines 300,
319 and 324 never applies. The caller then gets a refusal for a file that has no HEAD baseline at
all, which is the precise case the exemption was written for.

The staging instruction is also unnecessary as a prerequisite: the script stages untracked files
itself, `commit-pathspec.sh:458-460`, after every check has run. Staging by hand beforehand buys
nothing and costs the exemption.

Measured 2026-09-26 in `claude_usage_in_taskbar` (7 live session markers). Following SKILL.md step 8
literally, the first call refused:

```
[own-range] derivation:
  - tests/lightbox-composer-bridge.test.mjs: auto-derived own-range 1-119, UNVERIFIED (7 live session markers ...)
[foreign-hunk-check] UNVERIFIED, refusing ...: tests/lightbox-composer-bridge.test.mjs
```

The three tracked files in the same commit had caller-declared ranges and passed. Only the new file,
the one with nothing at HEAD to hide a peer's lines in, blocked the commit.

## Approach

Either end fixes it; the first is smaller and does not touch the concurrency logic 924 established.

1. **Preferred - key the exemption on "no blob at HEAD" instead of "untracked".** Replace the
   tracked-ness test at the exemption sites with `git cat-file -e HEAD:<path>` (or
   `git ls-tree HEAD -- <path>` being empty). A file staged as an add and a file never staged at all
   are identical for this check: neither has pre-existing lines. Keep the `live`/`untracked`
   classification itself as-is, since lines 386, 413-431 and 458-460 depend on it for staging and
   coverage; add the HEAD-baseline test as a separate predicate.
2. **Also update SKILL.md step 8** so the instruction stops working against the script: say that
   `commit-pathspec.sh` stages untracked files itself and the caller should NOT pre-`git add` them,
   and keep the manual `git add` wording only for the by-hand fallback path the same step already
   describes.

Do not relax the refusal for tracked files, and do not make the exemption unconditional. Both
reopen todo 924.

## Acceptance

- In a repo with 2+ live session markers, a commit whose pathspec includes one brand-new file and
  no other unchecked file completes without `--own-range` for that file and without
  `--force foreign-hunk`.
- The same commit still refuses if a TRACKED file in the pathspec has no declared range.
- A self-test covers both: one staged-add file and one tracked file, asserting only the tracked one
  triggers the refusal.
- `python ci/run_all.py` passes.

## Notes

Filed 2026-09-26 from a `claude_usage_in_taskbar` session, per root `CLAUDE.md`'s rule that findings
about the global `~/.claude` tree belong in this repo's backlog rather than the surfacing project's.

Peer sweep at filing time: `list_peers` showed two live sessions in `claude_usage_in_taskbar`
(`55dd049e`, `0e42f732`). Neither names the commit skill or `commit-pathspec.sh` in its session name
or recent channel messages - both were on view-harness/CSS and permission-modal work - so no peer was
asked. That is a weak signal, not proof nobody else has hit this.
- Completed by /loop-todos cycle 1 (2026-10-05). Script halves: eccffe6, 5d6f7b2, 61e7fae, f582722 (tests in skills/commit/test_*.sh); doc halves in skills/commit/SKILL.md (this commit) and e9f4620.
