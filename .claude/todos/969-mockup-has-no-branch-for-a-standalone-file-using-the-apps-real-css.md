<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=6, reconfirm-count=1, content-hash=cfa1d30a -->
<!-- duplicate-checked: grepped .claude/todos/ and done/ for "mockup". Nothing on the branch table; existing mockup todos are about disposal and preview push, not branch selection. -->
# /mockup has no branch for a standalone file built on the app's real CSS

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a third branch to `/mockup`'s step 2 table for the case that actually came up twice: a
self-contained HTML file that inlines the project's own stylesheets, rather than either a scratch
route inside the running app or hand-rolled Tailwind.

## Approach

`~/.claude/skills/mockup/SKILL.md` step 2 offers exactly two branches:

- **Real-component branch** - "Web stack with an existing, running component library"
- **Standalone-file branch** - "Flutter/mobile, or a web project with nothing reusable yet
  (greenfield)", built with Tailwind CDN + Phosphor CDN

Countoff is a Vite/React app with a full stylesheet set, so the table sends it to the
real-component branch. That branch was the wrong call there for a reason the table cannot see: a
scratch route lives in the running dev server, and the dev uses that server as his own workspace
(project memory `build-in-a-worktree-while-joe-tests`), so a Vite HMR update changes his open tab.
The standalone branch was also wrong, because hand-rolled Tailwind would not have proven anything
about how the real `.puck` / `.disc` / `.stage` / `.modal` rules behave.

What actually worked (countoff, 2026-09-07) was a hybrid the skill does not describe: a single
static HTML file whose `<style>` block is the project's real `src/styles/*.css` concatenated in at
build time by a small node script, with a marker in the source file. That gives the real cascade
and the real selectors, stays pushable to the preview panel as one self-contained file per step 6,
and never touches the dev's server. It caught genuine defects that hand-rolled CSS could not have:
initials rendering invisible because an inline `color` overrode `.disc { color: var(--bg) }`, and a
6px flex `gap` on `.stage-where` splitting a sentence into two flex items.

The skill's own rules also fight this case. "Reused CSS is frequently scoped to an ancestor class"
and the three verification checks in step 5 all assume the real-component branch; they apply
verbatim to this hybrid but the text does not say so.

Concretely:

1. Add the branch to the step 2 table, keyed on the real distinguishing condition - "a web project
   with real stylesheets whose dev server the dev is using live" - not on stack.
2. State the build shape: a `<!--APP_CSS-->` style marker in a `.src.html`, a small node script
   that splices the real stylesheets in, and the generated file as the artifact that gets previewed.
3. Say explicitly that step 5's three checks (gated selectors, computed style, measured geometry)
   apply to this branch too, since the whole point is that the real rules are in play.
4. Extend step 7's disposal list to name the `.src.html` and the build script alongside the
   generated `.html`.

## Acceptance

- `skills/mockup/SKILL.md` step 2 lists three branches, and the new one's trigger condition does
  not overlap ambiguously with the other two.
- A reader following the new branch can produce the artifact without inventing the marker-and-splice
  mechanism themselves.
- `python ci/run_all.py` passes (skill-frontmatter validation and the always-loaded token budget -
  the description is unchanged here, but the file is not).
