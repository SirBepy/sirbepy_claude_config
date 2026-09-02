<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "dev-server", "supervised-run", "dart run", "vite preview".
     done/441 shipped the guard. 857 is about /supervised-run's PORT handling, unrelated. -->
# dev-server-guard does not cover `dart run`, `vite preview` or `next start`

**Type:** task
**Origin:** ai

## Goal

Decide whether `hooks/dev-server-guard.py`'s pattern list should grow to the three long-lived launch
shapes it deliberately left out, and record the decision either way.

## Context

Filed 2026-09-02 from todo `441`'s builder report, which named all three as intentional omissions
rather than oversights. Two separate causes, and they want different answers:

**1. `dart run` was in the source todo but not in the dispatch.** Todo `441`'s own Approach step 3
lists "`dart run` for servers" in the intended pattern list. The dispatch prompt's authoritative
build list omitted it, so the builder left it out and said so. The builder also gave a substantive
reason beyond "not in my list": `dart run <script>` is a script-name distinction, not a
command-shape one, which is the exact ambiguity `441` warns about for `npm run` - a naive match
would catch one-off scripts that exit.

**2. `vite preview` and `next start` were never in either list.** The builder flagged them as
long-lived servers it chose not to guess at, keeping the negative space tight.

**This is a scope question, not a defect.** The guard does what it was asked to do, and the builder
surfaced the gap in the channel meant for it instead of silently widening. The reason to settle it
is that a partially-covered guard reads as full coverage to whoever relies on it later: someone who
sees `npm run dev` blocked will reasonably assume `vite preview` is too.

## Approach

1. Read `hooks/dev-server-guard.py`'s pattern list and `hooks/test_dev_server_guard.py`'s negatives
   first. The negatives are the constraint - `npm test` and `npm run build` must keep passing, and
   they are what a careless widening breaks.
2. `vite preview` and `next start` are command-shape matches, same as `next dev`, so they are the
   cheap half. Add them with fixture cases if wanted.
3. `dart run` is the genuine judgment call and should be answered explicitly rather than left
   pending: either match it only in shapes provably long-lived, or record in the guard's own
   docstring that it is deliberately uncovered and why, so this does not get re-filed.
4. Do NOT widen the guard from a general "block anything that looks like a server" instinct. `441`'s
   own Notes make the case: a false positive on a legitimate one-off would be severe, and a guard
   that fires on the test floor gets switched off.

## Acceptance

- A decision exists in writing for each of the three, in the guard's docstring or a sibling doc.
- Whatever is added is proven by a fixture case, and `npm test` / `npm run build` / a real
  `sv.ps1` invocation still pass.
- `python ci/run_all.py` exits 0.

## Notes

- Worth roughly a 5. Cheap, and it closes a gap that would otherwise be discovered as a surprise
  rather than as a documented boundary.
- `881` is a false-positive fix on the sibling guard from the same run. Unrelated mechanism, but if
  both are picked up, note that this todo makes the trigger set LARGER and `881` makes a trigger set
  more precise - the precision work is the safer one to do first.
