<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=1, content-hash=410ad14d -->
<!-- duplicate-checked -->
# 781 - `/flutter-e2e` should point at the project's own `e2e/lib/` before hand-rolling harness code

**Type:** skill-improvement
**Origin:** ai
Status: open

Skill: `~/.claude/skills/flutter-e2e/SKILL.md`

## The repeated manual step

Across one session on 2026-08-24 the same "click a Flutter web control by its semantics label"
helper was hand-written four times, in four throwaway scripts under `c:/tmp/pw-zng-claim/`, and got
it wrong twice before getting it right. Each rewrite rediscovered the same two traps.

## What the helper must encode

1. **Match the trimmed label for EQUALITY, never substring.** Parent `flt-semantics` nodes
   aggregate the whole page's `textContent`, so a substring test matches a full-page container whose
   rect starts near y=0. The click then lands on empty space and the feature looks broken. This
   produced two false "the fix does not work" readings in a single session.
2. **Collect every match and click the lowest on screen.** A page title and its CTA routinely share
   a label - `Decline request`, `Add your account`, `Get Started`.

Both are recorded in the zng-app memory `reference_flutter_web_playwright`, but a memory does not
stop the fifth hand-rolled copy.

## Also worth encoding

- Enable semantics once per page load, never again.
- Screenshot BEFORE enabling semantics, since it resets scroll.
- Assert on a `page.on('response')` hit rather than on a URL change when a click is meant to fire an
  API call - a swallowed tap is indistinguishable from a dead button otherwise.

## Update 2026-08-25 - the helpers already exist, in the project repo

Two things this todo did not know when it was filed:

1. **zng-app already ships them.** `e2e/lib/semantics.js` exports `enableSemantics`,
   `rearmSemanticsIfEmpty`, `clickByText`, `hasText`, `clickByMouse`, `screenshot` and
   `findSemanticsNodeHandles`; `e2e/lib/auth.js` exports `bootAuthedTo` / `bootUnauthedTo` /
   `gotoWithHangGuard`; `e2e/lib/browser.js` exports `launch`. Using them, two verification scripts
   were written with no hand-rolled matching at all (`e2e/verify-55162-claim-page.js`,
   `e2e/verify-55163-shared-toggle.js`, commits `d4aa79c` / `2ceb54a` in zng-app).

2. **The readiness check is the real trap, not the click.** Two runs were lost to
   `waitForSelector('flt-glass-pane')`, which times out after 120s because the glass pane sits in a
   shadow root and never reports visible. zng-app's `e2e/lib/auth.js:6-18` already documents this and
   polls the light-DOM `<flutter-view>` host instead.

## Approach

The skill's job is narrower than this todo first assumed. It does not need to author these
functions. It needs to:

1. Tell a session to look for an existing `e2e/lib/` (or equivalent harness folder) in the project
   BEFORE writing any Playwright helper code.
2. Name `<flutter-view>` as the mount signal and call out `flt-glass-pane` as the trap that reads as
   "the app is broken".
3. Carry the equality-not-substring and lowest-on-screen rules for the fallback case where a project
   genuinely has no harness yet.

## Acceptance

- `~/.claude/skills/flutter-e2e/SKILL.md` names the "check for the project's own harness first" step
  before any code-writing step.
- It names `<flutter-view>` and the `flt-glass-pane` trap.
- A cold session following the skill in zng-app reuses `e2e/lib/` instead of writing a fifth copy.

## Notes

Relocated from todo 185 in `c:\Users\tecno\Desktop\Projects\zng-app` via /cleanup-todos 2026-08-25:
it targets a global skill file, not the project, and per root CLAUDE.md a finding about the global
`~/.claude` tree belongs in this backlog.
