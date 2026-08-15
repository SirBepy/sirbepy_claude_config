<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=7, reconfirm-count=1, content-hash=59dee978 -->
# /mockup's fixed-width stage silently shows the wrong branch for viewport breakpoints

**Type:** skill-improvement
**Origin:** ai

## Goal

`/mockup`'s Staging section says to render each option "at its real target size" and to add "a
realistic-size stage ... clamped to the actual real width/height" (e.g. a phone viewport). For a
component whose responsive rules are **viewport** media queries (`sm:`, `md:`), a clamped-width stage
inside a wide browser window renders the **desktop** branch, so the stage shows a layout the app never
produces. The skill does not warn about this and the failure is silent.

## Context

Observed 2026-08-13, `fibo/frontend2`, a purchase-history card mockup.

- A stage 390px wide sat inside a 1248px viewport. A table column carrying `hidden sm:table-cell`
  stayed VISIBLE, because `sm:` tests the viewport (>= 640px), which was satisfied. The stage showed
  four cramped columns plus a horizontal scrollbar and read as a broken design.
- At a genuinely 390px viewport (`browser_resize`) the same code was correct: the column dropped,
  three columns, no scroll. Verified by measuring `colsVisible` and inner scrollers at both sizes.
- Cost: a builder reported "reflows, does not scroll", which was false against the stage and true
  against a real viewport; the orchestrator then reported the builder's claim as a defect to the dev
  and had to retract it.

Note this is the INVERSE of the case `/mockup` already handles well. A **container query** (which is
what much of that codebase uses, and what the existing project memory warns about) DOES fire correctly
in a fixed-width stage. So the skill's advice is right for container queries and wrong for viewport
queries, which is exactly why the gap is easy to miss.

A related trap found in the same session, worth the same paragraph: measuring overflow on the wrapper
rather than the scroller. A card div reported `scrollWidth == clientWidth` while a table wrapper inside
it was visibly overflowing with a scrollbar on screen. The card-level check said "no overflow" and was
believed.

## Approach

1. In `/mockup`'s Staging section, next to the realistic-size-stage bullet, add: determine FIRST
   whether the component's responsive rules are container queries or viewport media queries (grep the
   component for `@container` / `@[...]` versus `sm:` / `md:` / `lg:`).
   - Container query -> a clamped-width stage is valid, keep doing it.
   - Viewport media query -> a clamped-width stage LIES. Judge that breakpoint by resizing the actual
     viewport and capturing a separate shot, and label it as a real-viewport capture so the reader can
     tell the two apart.
2. In `/mockup` step 5's three non-negotiable checks, extend the geometric/numeric check: measure
   overflow on the element that actually scrolls (walk descendants for
   `scrollWidth > clientWidth + 2`), never only on the outer container.
3. Consider stating plainly that a mockup board mixing both kinds of stage must label which is which,
   since an unlabelled fake-width stage beside a real-viewport shot is worse than either alone.

## Acceptance

- `/mockup`'s SKILL.md distinguishes container queries from viewport media queries where it currently
  says "real target size", and prescribes viewport resizing for the latter.
- Step 5's measurement check names the inner-scroller rule.
- A future session following the skill cannot produce a 390px stage of a `sm:`-gated component and
  present it as mobile behaviour.
