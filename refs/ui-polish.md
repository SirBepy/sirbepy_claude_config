# UI polish bar

This is the floor for any change a user sees, in any project with a UI. A feature that works but
pops, shifts or sits flat is not done. Read this file before you write a UI brief or UI code. Paste
the checklist at the bottom into every brief that builds or changes UI. The incident behind it is
in `refs/incidents.md` under "UI & visual changes - the UI polish bar".

**Skips:** copy-only or text-only edits, backend and config work, CLI and TUI output. Items 5-8, 10,
12-13 and 15-16 are web CSS. Flutter, native Android and Roblox apply the same intent with their own
platform equivalents.

## Where this sits next to other guidance

- **Method:** run `impeccable polish` and `impeccable animate` (`~/.claude/skills/impeccable/`) on
  the diff. This file adds the rules they lack and settles the conflicts below.
- **App UI overrides "restraint".** Some guidance is tuned for landing pages: impeccable's "one
  authored moment" (`animate.md`, `craft-floor.md`), its "do not animate a static area merely
  because it exists", and Anthropic's frontend-design skill. In app UI, every visible state change
  moves. Restraint governs how far and how long an element moves, never whether it moves.
- **A project's own tokens win over any number here.** Example: Conductor's `--motion-fast`,
  `--motion-base` and `--motion-ease` in `src/styles/tokens.css`. If no token covers a range below,
  add one token, e.g. `--motion-slow` at about 300ms, to the token file. Never write a raw value
  into each rule. In a client repo, adding a token needs the brief's OK.

## Motion

1. **Nothing snaps; frequency picks the duration.** Joe's rule, 2026-11-17: an action done many
   times a day still animates, only faster.
   - Frequent or keyboard-started actions: 100-180ms. Examples: menu toggle, Ctrl+N jump, hover,
     press, tab switch.
   - Structural changes: 200-350ms. Examples: enter, exit, expand or collapse, reorder, panel open.
   - Occasional moments may be slower. Examples: first load, a finish celebration.

   Ship and preview at these real-speed (1x) values. On 2026-11-17 Joe approved the chat heads
   board at 1x and said "stop doing speed 0.25, i want it speed 1x". A single 2026-10-27 pick of
   4x-slowed timings for one entrance is not the default.
2. **Every state change gets a transition.** That covers enter, exit, expand or collapse, reorder,
   selected, open or closed, loading to loaded, and count changes. Content that appears or
   disappears only through a `display` swap or a conditional render fails.
   - **Enter:** use `@starting-style` (Safari 17.5+), or add an `is-opening` class one frame after
     the node is inserted.
   - **Exit:** keep the node in the DOM until `transitionend`, then remove it. If the node is
     removed instantly, it pops, whatever the CSS says.
3. **Exit mirrors enter.** It leaves along the path it came in and runs a little faster. When a
   neighbour leaves, the others slide into the gap and never jump.
4. **Easing:**
   - Enter, exit and movement: ease-out (the project's easing token, or
     `cubic-bezier(0.22, 1, 0.36, 1)`).
   - Colour and opacity: plain `ease`.
   - Never ease-in on UI. No bounce unless the design asks for it.
5. **Animate transform and opacity.** Height animates through `grid-template-rows: 0fr -> 1fr`, which
   works in every engine. Never guess a `max-height`. `interpolate-size: allow-keywords` works
   only in Chromium, so it is never the only height mechanism in anything that ships to macOS,
   Safari or WKWebView. Never start from `scale(0)`. Start from 0.9-0.97 with opacity 0, and never
   use `transition: all`: name each property.
6. **Make it interruptible.** For anything a user can trigger twice quickly (a toggle, an expand, a
   hover), use CSS transitions, which retarget from the current value. A keyframe restarts from
   zero, so use keyframes only for one-shot moments. Put them on a class removed at
   `animationend`, never on the base rule, or they replay whenever another class toggles.
7. **Stagger lists by 30-60ms per item.** Cap the stagger so the last item starts within about
   250ms. Popovers, menus and tooltips grow from their trigger: set `transform-origin` there.
8. **Reduced motion keeps the timing and swaps the movement for a fade.** Never turn motion off
   entirely.
9. **Never paint an unstyled frame.** If a surface can render before its styles land, it shows
   nothing until they do.
10. **A data update never replays motion.** A status, count or ring update patches only the parts
    that changed. Never rebuild an element's insides wholesale, or every enter animation inside it
    replays, and the element under the pointer twitches each time the data ticks. Seen 2026-11-17:
    a hovered chat head bounced on every status update.
11. **Motion code that already exists stays on.** When a new surface reuses an animated helper (a
    reconciler with FLIP, enter and exit), never pass its animation-off switch because "nothing
    re-sorts". No re-sort means no automatic reordering. Enter, exit and Joe's own drag still
    move.

## Interaction states

12. **Everything clickable has hover, active and focus-visible states.**
    - Hover is visible but quiet.
    - Press: buttons and small controls go to about `scale(0.97)`. Rows and links press with a
      background change only, because a scaled full-width row makes the list jitter.
    - Focus: use `:focus-visible` with a ring. Never a bare `outline: none`.
13. **Hover styles sit under `@media (hover: hover)`**, so they never stick after a tap on a phone.
    Every hover-revealed control also needs a touch path.
14. **The cursor matches the action:** `pointer` for click, `grab` and `grabbing` for drag,
    `default` when disabled. Leave no dead gaps between adjacent hit targets: use padding inside
    the targets, not margin between them.

## Layout stability

15. **A hidden control takes no space.** A control revealed on hover overlays the row: absolute
    position, with a fade or gradient behind it.
    - Reveal it on `:hover` and on `:focus-within`.
    - Toggle `opacity` together with `pointer-events` or `visibility`, never `width` or `display`.
    - When hiding with `visibility`, delay the hide (`transition: opacity .15s, visibility 0s .15s`),
      or the fade-out is cut short.
    - At rest, the row's content sits flush with its edge.
    - Check: the row's bounding boxes are identical hovered and at rest.
16. **Nothing reflows on hover or select.** No font-weight change on hover or selection. Use
    `tabular-nums` for counts and times that tick.
    **Menus, popovers and hover cards stay inside the viewport from every anchor**, including a
    control at the screen's edge: clamp both axes, and flip to the other side when there is no
    room. Seen 2026-11-17: the chat heads' right-click menu ran off the left edge.

## Drag and reorder

17. **Neighbours move aside live while dragging,** by FLIP or by transform positions. An insertion
    line alone fails.
    - The dragged item lifts: about `scale(1.03-1.05)` plus a shadow.
    - It follows the pointer, and on drop it transitions into its slot. It never teleports.
    - A drop the backend refuses animates back to the item's old slot.

## Style and consistency

18. **Reuse before inventing.** Before you style a new surface, open the two or three most polished
    sibling surfaces. Reuse their tokens, radii, easing and row patterns. The new surface must look
    like part of the same app.
19. **Show the real items instead of a bare count when the user would act on them:** avatars,
    names, a preview. Never add a ring or a bar as decoration (impeccable's craft-floor refusal
    still holds).

## Proof before merge

20. Run `impeccable polish` and `impeccable animate` on the changed surface. Fix what they find in
    one bounded pass.
21. **Joe sees the motion before merge.**
    - A new surface or new motion gets a real-speed clip of its key state changes, one caption
      per clip. Add a 0.25x clip only when Joe asks for one. In Conductor, use the motion
      preview recipe in project memory; elsewhere, use a Playwright video.
    - A tweak to existing motion or styling needs only before and after stills.

    A sub cannot show Joe anything itself: it records the clips, and the parent chat shows them.
    This rule replaces the plain-screenshot step in global CLAUDE.md whenever there is motion.
22. If the project has view or e2e specs, add assertions for the risky rules:
    - hovering leaves the row's bounding boxes unchanged
    - the expanding element declares a transition
    - the siblings' transforms change during a drag
23. **Every deferral reaches Joe in the final report,** not only in a design doc or a todo. Write
    one line per design item not built, naming the item and the reason. If a deferral changes what
    Joe will see, stop and report it to the parent instead of deferring silently.

## Checklist to paste into every UI brief

```
UI polish bar (~/.claude/refs/ui-polish.md, read it in full before building). Done means:
- In app UI every visible state change moves. Impeccable's "one authored moment" / restraint
  governs distance and duration, never whether something moves.
- Motion uses the project's tokens: frequent or keyboard actions 100-180ms, structural changes
  (enter, exit, expand, reorder, open) 200-350ms. Enter via @starting-style or an is-opening class;
  exit keeps the node until transitionend. Exit mirrors enter, neighbours slide instead of jumping,
  transitions are interruptible, reduced motion fades. Height via grid-template-rows 0fr -> 1fr.
- Everything clickable has hover (under @media (hover: hover)), active and focus-visible states;
  rows press with a background change, not a scale.
- Hover-revealed controls overlay the row, also show on :focus-within, and reserve no space;
  nothing reflows on hover or select; menus and popovers stay on screen from every anchor.
- A data update patches in place and never replays an animation; existing animated helpers
  stay switched on.
- Drag reorder moves neighbours aside live and settles on drop.
- Styled like the most polished sibling surfaces (same tokens, radii, easing, row patterns); real
  items shown instead of bare counts where the user acts on them.
- Run `impeccable polish` and `impeccable animate` on the diff and fix what they find.
- Report: a real-speed clip of each new animated state change (stills for a tweak), and one
  line per design item not built, with the reason.
```
