# Fibo Frontend — Atom-Level Style Guide

Condensed from `frontend/DESIGN-SYSTEM-SPEC.md` (verbatim code-derived spec —
read that for `file:line` citations). This file is a quick-reference for
picking the right `@fibo/ui` component and token while reviewing a diff.

---

## Design tokens

### Colors (light theme, `frontend/src/index.css`)

| Token | Hex | Use for |
|---|---|---|
| `--background` | `#f8fafc` | Page background (NOT pure white) |
| `--foreground` | `#0f172a` | Primary text |
| `--card` | `#ffffff` | Card / sidebar / header surfaces |
| `--primary` | `#1738dd` | Brand blue — CTAs, focus ring, active states |
| `--primary-foreground` | `#ffffff` | Text/icon on primary fill |
| `--secondary` / `--muted` / `--accent` | `#f1f5f9` | Same value, intentional — subdued surfaces |
| `--muted-foreground` | `#64748b` | Secondary/body-muted text |
| `--destructive` | `#ef4444` | Errors, dangerous actions |
| `--border` / `--input` | `#e2e8f0` | Every border, input border |
| `--ring` | `#1738dd` | Focus ring = primary |
| `--chart-1..5` | `#1738dd #4f63e8 #6b8aff #94a3b8 #cbd5e1` | Charts only — never UI rows |
| `--sidebar` | `#ffffff` | Sidebar bg |
| `--sidebar-primary` | `#1738dd` | Active nav item bg |

Dark theme flips `--primary` to `#fb7185` (coral/rose); other tokens have dark
variants defined in `index.css` (`.dark` block).

**Banned in rows/badges**: purple, violet, fuchsia, pink, indigo (all read as
"purple" at small sizes). No raw hex or arbitrary Tailwind values
(`bg-[#...]`, `p-[13px]`) outside generated tokens. See
`design-principles.md` §12 for the full rule and the one standing exception
(Recipe Editor violet badges).

### Fonts

| Usage | Font | Class |
|---|---|---|
| Body text (default) | DM Sans | — (base) |
| Headings `h1`–`h6`, manual emphasis (PageHeader title, filter section headers) | Plus Jakarta Sans | `font-heading` |

### Radius scale

| Token | Value | Used on |
|---|---|---|
| `--radius-sm` | 6px | DropdownMenu items, mobile segmented control |
| `--radius-md` (`rounded-md`) | 8px | Button, Input, Select, Alert, table cells |
| `--radius-lg` (`rounded-lg`) | 10px | Dialog content, sidebar nav links, Tabs track |
| `--radius-xl` (`rounded-xl`) | 14px | Card root, supplier-group panels, empty-state boxes |
| `--radius-2xl` | 18px | — |
| `--radius-3xl` | 22px | Sidebar shell, filter drawer's inboard rounded edge (`md:rounded-l-3xl`) |
| `rounded-full` | pill | Badges, Avatars, FABs, sidebar nav-badge, icon-stepper buttons, PageHeader filter icon |

### Spacing / row rhythm

- Standard row padding: `px-4 py-3` (~50–54px effective with 2 lines of text).
- Card padding: `py-6` vertical, `px-6` horizontal on subparts (Header/Content/
  Footer), `gap-6` between them.
- Dialog content: `p-6`, max width `sm:max-w-lg` (512px).
- Sheet (side drawer): default `w-3/4` capped `sm:max-w-sm` (384px); the
  filter drawer overrides to `md:w-1/3` on desktop.

---

## Component picks

| Need | Use | Not |
|---|---|---|
| Any button | `Button` (`default`/`destructive`/`outline`/`secondary`/`ghost`/`link` variants; `default`/`sm`/`lg`/`icon`/`icon-sm`/`icon-lg` sizes) | raw `<button>` (except documented FAB/stepper bespoke overrides below) |
| Text/date/number input | `Input` (`h-9`, `bg-transparent`, `rounded-md`) | custom styled input |
| Search with icon + clear | `SearchInput` (wraps Input with leading icon + clear-X) or `CompactSearchInput` in PageHeader context | ad-hoc absolute-positioned icon overlay per page |
| Status/category pill | `Badge` (`rounded-full`, pill shape — NOT `rounded-md` like generic shadcn) | colored `<span>`/dot/circle |
| Small status pill inside a list row | `Badge variant="outline"` + `className="text-[10px] px-1.5 py-0 leading-4 ..."` recolor (amber/emerald/red/muted per meaning) | a new cva variant (none exist for success/warning — recolors are the house pattern) |
| Content grouping (settings section, metrics summary) | `Card` → `CardHeader`(+`CardTitle`/`CardDescription`) → `CardContent` | wrapping the main list when it's already a Table |
| Tabular data with many scalar columns + inline expand | `Table`/`TableHeader`/`TableRow`/`TableHead`/`TableCell` (list-row pattern §4a) | — |
| Master list of clickable rows navigating to detail | Hand-built row per PATTERNS.md §4b (`button` w/ `border-b px-4 py-3`) — the Table primitive is largely unused for this | `<Table>` |
| Modal confirmation / form popup | `Dialog` (centered, `rounded-lg`, `p-6`, scrim `bg-black/50`) | — |
| Destructive confirmation | `AlertDialog` (`size="sm"` clamps `max-w-xs`) | plain `Dialog` |
| Filter drawer | `FilterSheet`/`FilterSection`/`FilterChip` (`src/components/filters/FilterSheet.tsx`) — Dialog-based, popup desktop / bottom sheet mobile | raw `Sheet` primitive |
| Navigation / side panel drawer | `Sheet` (`side="left"`/`"right"`) — classic side drawer at every breakpoint | for filters |
| View-switcher tabs | `Tabs` — Fibo's default is the **pill** variant (`bg-muted` track, white active pill w/ `shadow-sm`), NOT underline. A `line` (underline) variant exists but is unused on primary pages | hand-rolled tab buttons (except the one documented mobile segmented-control exception, InventoryCountPage) |
| Multi-select with search | `MultiSelect` (custom, not Radix) — pills w/ X, `rounded-full` | — |
| Row/page kebab actions | `KebabMenu` — DropdownMenu on desktop, bottom Sheet on mobile | — |
| Dropdown / single select | `DropdownMenu`, `Select` (`h-9`, same shell as Input) | — |
| Toggle | `Switch` (`default` 18×32px, `sm` 14×24px; checked = `bg-primary`) | — |
| Divider | `Separator` (1px `bg-border`) | a manual `<div className="border-b">` — though pages do use plain divs for panel-splitting dividers by convention (documented exception) |
| Alert banner | `Alert` (`default`/`destructive` only — no info/warning/success cva variant; pages roll inline `bg-destructive/10` etc. for those) | — |
| Loading indicator | Lucide `<Loader2 className="animate-spin text-primary">` — the dominant pattern across pages, NOT the bespoke `LoadingSpinner` component (that's reserved for auth flows + AppLayout) | a new bespoke spinner |
| Avatar | `Avatar` (`size-8`, `rounded-full`) | — |
| Nothing exists yet (no generic `Skeleton` primitive) | Bespoke per-row skeleton component mirroring the real row geometry (e.g. `PurchasesRowSkeleton`) | inventing a generic one ad hoc — check if `@fibo/ui`'s `Skeleton`/`SkeletonRows` already covers it first |

### Bespoke, documented exceptions (not violations — these are the house pattern)

- **Round FAB**: raw `<button>` (not `Button`) — `h-10 w-10 rounded-full
  bg-primary text-primary-foreground shadow-lg hover:brightness-110`. The
  `Button` component has no `rounded-full` size, so pill FABs are
  intentionally bespoke.
- **Stepper +/- buttons**: `<Button variant="outline" size="icon"
  className="h-8 w-8 rounded-full">` — round override of the square `icon`
  size, used in shopping-cart/inventory-count quantity steppers.
- **Mobile segmented control** (InventoryCountPage): hand-built `rounded-md`
  track with `rounded-sm` segments, visually mirrors `Tabs` `default` variant
  but renders independently — used when a trailing count needs different
  opacity treatment than `Tabs` supports.

---

## Icon convention — flag on sight

Fibo's global project rule mandates **Phosphor Icons** for all new
frontend icon usage (`@phosphor-icons/react` for React code; never inline SVG
or a custom icon set).

**Known inconsistency**: the actual codebase currently imports **Lucide
React** everywhere (`Sidebar.tsx`, `PageHeader.tsx`, every page — confirmed in
`frontend/CLAUDE.md`'s stack table and throughout `DESIGN-SYSTEM-SPEC.md`).
This is a real, unresolved drift between the mandated convention and shipped
code.

- Do not silently "fix" this in a design review by picking one library.
- Flag any NEW file that imports Lucide as not matching the Phosphor mandate,
  but note in the same finding that it matches 100% of existing surrounding
  code — this is a call for a human decision (migrate everything, or update
  the mandate to Lucide), not a mechanical fix.

---

## Animation / transition conventions

| Class | Effect | Duration | Applied to |
|---|---|---|---|
| `animate-page-in` | Fade in + 8px slide up | 0.4s ease-out | Outer page wrapper (`<div className="space-y-6 animate-page-in">`) |
| `animate-page-in-up` | Fade in + 16px slide up | 0.5s ease-out | Some auth/onboarding pages |
| `animate-card-in` | Fade in + 12px slide up + slight scale | 0.4s ease-out | Cards used for emphasis, often with `style={{ animationDelay: '0.15s' }}` for staggered entrance |

- Dialog/Sheet open animations use `tw-animate-css` (`zoom-in-95` /
  `fade-in-0` for Dialog; `slide-in-from-right` etc. for Sheet) — built into
  the primitives, not per-page.
- Sidebar width transition: `transition-[width] duration-300
  ease-[cubic-bezier(.4,0,.2,1)]` on expand/collapse.
- Don't sprinkle animation classes outside these documented spots — PATTERNS.md
  §9 is explicit that this is the full list.

---

## Layout shell reference

- **Sidebar**: floating `<aside>`, `rounded-3xl border shadow-sm`, `my-3.5
  ml-6 mr-2`, expanded `w-[17rem]` / collapsed rail `w-[4.625rem]`. Active
  top-level item = full `bg-primary` fill; active child link = primary text
  only, no fill.
- **Header**: `h-16 border-b bg-card`, tenant switcher + Avatar menu on the
  right.
- **PageHeader**: breadcrumb (uppercase, `tracking-[1.5px]`, last segment
  `text-primary`) → title (`font-heading`, 3 size variants) → subtitle row
  (`[subtitle | actions]`) → optional round 36px filter button → hairline
  `border-b` divider → optional full-width search.
- **Master/detail split** (StockItemsPage, PurchasesPage pattern): master
  pane `md:w-2/5` when a detail is open, both panes scroll independently with
  a slim `w-1.5` scrollbar; mobile fully swaps master↔detail (no slide
  animation, plain route swap).
