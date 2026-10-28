<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=1, content-hash=43709beb -->
# /mega-todos assumes a Rust/Tauri project and mis-states its own abort gate

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix two defects found by running `/mega-todos` for the first time against a React/Vite package
(fibo's `frontend2/`) on 2026-08-11. Both made the skill harder to follow than it needed to be.

## Context

**1. The verify ladder is written entirely in Cargo terms.** Its per-batch barrier is
`cargo check --manifest-path src-tauri/Cargo.toml` and its every-10-to-15-todos full floor is
`cargo build`. It also says "Rust - nothing yet; cargo is too slow to run per todo". A frontend
project has no equivalent of any of that, so the whole ladder had to be re-derived on the fly:
per-todo `npx tsc --noEmit` plus the relevant vitest file, per-barrier `npm run lint` repo-wide,
periodic `npm run lint` + `npm run test` + `npm run build`.

**2. The Step A preflight table's `GIT_FLOW.md` row is wrong as written.** It says that if
`GIT_FLOW.md` exists at the repo root, "Abort the run and tell the dev to branch first". The stated
reason is that agents would each stall on `/commit`'s `AskUserQuestion` branch-protection gate. But
that gate is three-part: it only fires when the branch ALSO matches a protected-trunk name
(`main`/`master`/`develop`) AND the repo has a remote. On a feature branch the file's presence is
harmless. Taken literally the rule bricks the skill in every repo that documents its git flow, which
is most of them. The 2026-08-11 run had to override it to proceed at all.

## Approach

File: `C:\Users\tecno\.claude\skills\mega-todos\SKILL.md`.

1. Rewrite the "Verify ladder" section in terms of ROLES rather than commands: a cheap per-todo
   check scoped to what the agent touched, a per-barrier repo-wide check, and a periodic full floor.
   Let the project supply the actual commands, and demote the Cargo lines to one worked example
   among several. Add a frontend example alongside it.
2. Change the Step A check from "`GIT_FLOW.md` at repo root" to "`GIT_FLOW.md` at repo root AND HEAD
   matches a protected-trunk name", so it mirrors `/commit` step 1a's real condition instead of a
   loose proxy for it.

## Acceptance

- A reader on a non-Rust project can derive the verify ladder from the skill text without inventing
  it.
- Running `/mega-todos` on a feature branch in a repo that has `GIT_FLOW.md` does not trip the abort
  gate; running it while sitting on `develop` still does.

## Notes

- Done 2026-08-12, commit c930934. Verify ladder rewritten by ROLE (cheap per-todo / per-batch barrier / full floor / final barrier) with three worked stack examples including a no-build-system repo; Step A's GIT_FLOW row now requires all three of /commit step 1a's real conditions.
