# Fibo Frontend — Design Review Checklist

Source of truth: `frontend/PATTERNS.md` and `frontend/DESIGN-SYSTEM-SPEC.md`
(read those for full detail — this file is the graded rubric, not a copy).
Anchor pages to compare against: `DocumentsPage.tsx`, `PurchasesPage.tsx`,
`BankStatementsPage.tsx`.

Grade each diff against the sections below. Flag any unchecked item as a
finding with severity (blocker / should-fix / nit).

---

## 1. PageHeader usage

- [ ] Page uses `<PageHeader>` (`src/components/PageHeader.tsx`) — never a
      hand-rolled title block. `<PageHeader>` is the first child of the page
      wrapper; nothing floats above or beside it.
- [ ] `breadcrumbs` is set with a real hierarchy (e.g.
      `[{label:'Inventory'},{label:'Products & Stock'}]`), not just the page
      name. Missing breadcrumbs = the title row crowds the app header above —
      flag it.
- [ ] `actions` holds action buttons (Refresh, Export, Rebuild, primary CTAs)
      and/or the compact inline search — it's items-center aligned with the
      subtitle.
- [ ] `filterLeadingActions` holds buttons only when there's also a filter
      circle (`onFilterToggle`) for them to sit next to — it's items-start
      aligned with the title and looks top-anchored/crowded without a filter
      circle to balance it. If a page has no filter drawer, action buttons
      belong in `actions`, not here.
- [ ] `search` (full-width prop, renders below the header border) is used
      **only** when no other action buttons compete for header space.
      Otherwise the compact inline search belongs in `filterLeadingActions`
      (§2).
- [ ] `titleTrailing` (big right-aligned value) reserved for detail pages
      (invoice total, balance) — baseline-aligned to the title.
- [ ] No section-level title duplicated above the list when `<PageHeader>` is
      already present.
- [ ] No subtitle set? Search + action buttons should be in
      `filterLeadingActions` to avoid an empty-subtitle vertical gap.

## 2. Search placement

- [ ] Exactly one search input per page, and it lives in the PageHeader —
      never a separate `<Input>` in a Card above the list, never inside the
      filter drawer.
- [ ] Compact inline search (`CompactSearchInput`, via `filterLeadingActions`)
      is used when the page also has action buttons. Desktop renders `h-9
      w-56`; mobile collapses to an icon-only button that expands on click —
      don't ship a narrow always-visible mobile input (a documented past
      mistake, `w-32`, ~60px usable text).
- [ ] Full-width `search` prop used only when there are no buttons fighting
      for the header's right side.
- [ ] Placeholder follows the house convention: `Search by <thing>...` or
      `Search <things>…`.

## 3. Filter drawer

- [ ] Filters live in `<FilterSheet>` (`src/components/filters/FilterSheet.tsx`)
      — a `Dialog`-based popup on desktop, bottom sheet on mobile. Never an
      inline filter panel above the list, and never the raw `<Sheet>`
      primitive (that's reserved for navigation/side panels and stays a
      classic side drawer at every breakpoint).
- [ ] Filter state uses the pending-state pattern: `pending*` vars in the
      drawer, separate live vars driving the list, `commitPendingAndClose`
      copies pending → live on Done/dismiss.
- [ ] Footer has `Clear all` + `Done`, both `flex-1`; `clearDisabled` passed
      when nothing is applied.
- [ ] "Sort by" lives inside the FilterSheet as a `FilterSelect` — never a
      separate "Order by" Tabs row or a standalone dropdown next to search.
      The filter button's active-dot should reflect sort too.
- [ ] Heavy long-running admin actions (Rebuild, Reset, Reindex) are NOT in
      the filter drawer — they get their own `<Dialog>` triggered from
      `filterLeadingActions`.
- [ ] Page-level jump-off links (e.g. "All charts") are not filters — they go
      in `filterLeadingActions` as a small icon button (`size="icon-sm"` +
      `Tooltip`), not buried in the drawer.

## 4. List-row pattern (pick exactly one of three — no fourth)

| Pattern | Use when |
|---|---|
| §4a Expandable table | rows have many comparable scalar columns, click expands inline detail (`<Table>` from `@fibo/ui`) |
| §4b Master-detail button rows | click navigates to a separate detail route |
| §4c Stat-list rows | identity + 2–4 named numeric metrics + a prominent right-aligned headline metric, click expands an inline log |

Checks common to all three:
- [ ] Row padding `py-3` — never tighter.
- [ ] Primary text `font-medium` (`text-lg font-medium` for master-detail).
- [ ] Secondary metadata `text-sm text-muted-foreground`.
- [ ] Status/state shown via `<Badge>` variants only — no ad-hoc colored
      dots/circles/inline flags. Missing Badge variant → ask for one, don't
      roll a one-off.

§4a specifics:
- [ ] `cursor-pointer hover:bg-muted/50` (or `hover:bg-accent/50`) row class.
- [ ] Expansion is a sibling `<TableRow>` with one `<TableCell colSpan={N}>`,
      `bg-muted/30` or `/20`.

§4b specifics:
- [ ] Selected row: `bg-primary/10 hover:bg-primary/10`. Unselected:
      `bg-background hover:bg-accent/30 active:bg-muted/50`.

§4c specifics:
- [ ] **One** column-header row at the top (`hidden md:flex`) — never
      per-row column labels repeated on every row.
- [ ] Header row uses identical widths/gaps as data rows so cells line up.
- [ ] Data cells use `hidden md:contents` to disappear on mobile while
      staying direct flex children on md+.
- [ ] Header row padding `py-2`; data rows `py-3`.
- [ ] Headline metric `text-base font-semibold`; secondary metrics `text-sm
      font-medium`; non-numeric cells (dates, UOM) `text-xs
      text-muted-foreground`.
- [ ] UOM is its own column, never appended to a numeric value.
- [ ] At most 3 colored metrics per row (see §6 palette below).

## 5. Empty / loading / error states

- [ ] Uses the shared atoms from `@/components/query` — `ListLoading`,
      `ListEmpty`, `QueryError` — never hand-rolled markup duplicating them.
- [ ] `ListEmpty` passes `bare` when already inside a `<Card>` (avoid double
      chrome).
- [ ] **Every list query renders an `isError` branch.** Silently falling
      through to the empty state on error is a defect — flag it as a
      blocker.
- [ ] `QueryError` picks the right variant: `replace` (blocks the list, has
      Retry) vs `banner` (non-blocking strip) for pages that stay usable
      when one read fails.
- [ ] Empty-state copy is at most two sentences: what's missing + what to
      do. When filters are active and the result is empty, appends "Try
      adjusting your filters."
- [ ] Nullable-prop guard placement: a zero-hook presentational component may
      `return null` internally; a component with hooks/effects/mount-tied
      behavior must be guarded externally (`{value && <Comp/>}`) at the call
      site instead.

## 6. Data hooks / query layer (flag if a page bypasses this)

- [ ] All queries/mutations live in `src/hooks/queries/<domain>.ts` — no
      inline `useApiQuery`/`useApiMutation` in page files.
- [ ] Mutations use `useApiMutation` with `invalidates`/`invalidatesGlobal`
      from `keys.ts` — raw `api.post/put/delete` + `refetch()` as a mutation
      substitute is a review-blocker on new/touched code (exempt: documented
      multi-step imperative pipelines, e.g. per-file upload loops).
- [ ] `tenant_id` is never passed into a hook as a caller-supplied variable —
      the hook derives it from `useAuth()` internally, even for admin-global
      endpoints where it travels in the POST body.
- [ ] Cache scope (`useApiQuery` vs `useApiQueryGlobal`) follows the shape of
      the DATA, not the URL path — tenant-scoped rows use the tenant-prefixed
      keys even behind an `/admin/…` path.

## 7. Action buttons

| Role | Variant | Size |
|---|---|---|
| Refresh | `outline` | `sm` |
| Heavy admin action (Rebuild/Reset/Export) | `outline` | `sm`, opens confirm Dialog |
| Primary CTA (Save/Submit/Create) | `default` | `default` |
| Inline row action | `outline` | `sm` (or `h-7 text-xs` ultra-compact) |
| Pagination | `outline` | `sm` |
| Filter/sort chip | `default`/`outline` by active state | `sm`, inside FilterSheet only |

- [ ] No two adjacent buttons share the same variant (usually `outline` +
      `default`).
- [ ] Icon-only buttons use `size="icon"`/`size="icon-sm"` and always have an
      `aria-label`.
- [ ] Destructive actions in page chrome use `<AlertDialog>` confirmation, not
      a plain `<Dialog>`.

## 8. Tabs

- [ ] `<Tabs>` sit after the PageHeader border, before the list; `TabsList`
      is `mt-4` from the header border.
- [ ] No search/filter row wedged between Tabs and the list.

## 9. Cards

- [ ] Cards group content (settings section, metrics summary) — never wrap a
      list that's already a `<Table>` (avoids nested borders).
- [ ] `<Card>` → `<CardHeader>`(+`<CardTitle>`/`<CardDescription>`) →
      `<CardContent>` shape used as-is; no hand-tuned padding overrides.

## 10. Animations

- [ ] Page entrance: `animate-page-in` on the outer `space-y-6` wrapper.
- [ ] Card entrance (for emphasis only): `animate-card-in`, optional
      `animationDelay: '0.15s'`.
- [ ] No animation added outside these two documented spots.

## 11. Typography

- [ ] Headings (`h1`–`h6`, PageHeader titles, filter-drawer section headers)
      use **Plus Jakarta Sans** (`font-heading`).
- [ ] Body text uses **DM Sans** (the default, no override needed).
- [ ] PageHeader title size matches its variant: `default` = `text-3xl
      font-bold`, `detail` = `text-[26px] font-bold`, `compact` = `text-lg
      font-semibold`.

## 12. Color palette (§10 of PATTERNS.md) — hard bans

- [ ] **No `text-purple-*`, `bg-violet-*`, `border-fuchsia-*`,
      `text-pink-*`, `text-indigo-*`** anywhere in rows, badges, or status
      signals. `indigo-600` reads as purple at small sizes — rejected on
      sight. `--chart-2` (#4f63e8) is reserved for charts, never UI rows.
      **Known standing exception**: Recipe Editor "Produced" badges
      (`ItemInputNode.tsx`, `NodeInspectorPanel.tsx`) use violet — this is a
      deliberate, still-open grandfather in `check-palette.mjs`'s
      `SKIP_PATHS`, not a precedent to extend elsewhere.
- [ ] **No raw hex** in `frontend/src/**/*.tsx` outside generated tokens — no
      `bg-[#1738dd]`, no `p-[13px]` arbitrary Tailwind values.
- [ ] New per-row/badge signal colors come only from the documented
      status/data-tag palette:

  | Meaning | Class |
  |---|---|
  | Positive / inbound (Received, OK) | `text-emerald-600` |
  | Action / outbound (Consumed, Used) | `text-orange-600` |
  | Sales / POS activity (Sold) | `text-yellow-600` |
  | Caution / low (low stock, warning) | `text-amber-600` |
  | Negative / over-limit | `text-red-600` |
  | Production / internal transformation | `text-blue-600` |
  | Neutral / unspecified | `text-foreground` (default) |

  Yellow (sales, always positive) and amber (caution) are visually close but
  mean different things — flag any swap.
- [ ] At most 3 colored metrics per row — beyond that the row "looks like a
      parrot" per the doc.
- [ ] Semantic CSS-var tokens used via Tailwind utilities, not hardcoded:
      `--primary` (`#1738dd` light / `#fb7185` dark) for brand/CTA/focus,
      `--destructive` (`#ef4444`) for errors/danger, `--muted-foreground`
      (`#64748b`) for secondary text, `--border` (`#e2e8f0`) for
      dividers/borders.
- [ ] A genuinely new semantic color is added as a CSS var in `src/index.css`
      (+ Figma Variable) — never a sneaked-in Tailwind hex.

## 13. Accessibility

- [ ] No `<button>` nested inside another `<button>`. A row that must be
      clickable AND contain nested interactive elements (chips, links,
      inline buttons) uses the shared `RowButton` primitive
      (`src/components/RowButton.tsx`) — a `<div role="button" tabIndex={0}>`
      with Enter/Space activation — not a raw `<button>` wrapping other
      controls.
- [ ] Icon-only buttons carry `aria-label` (see §7).
- [ ] Fragment-wrapped list rows (expandable §4a/§4c rows) use a stable `key`
      on the `<Fragment key={row.id}>`, not array index.

## 14. Mobile / bottom-sheet expectations

- [ ] Filter drawer (`FilterSheet`) renders as a centered popup on desktop
      and a bottom sheet on mobile automatically (Dialog's `mobileSheet`
      default) — don't special-case this per page.
- [ ] Compact search collapses to an icon button on mobile (<md) per §2 —
      never a cramped always-on narrow input.
- [ ] §4c stat-list rows drop data columns on mobile via `hidden md:contents`
      while keeping row identity + expand affordance visible.

## 15. Pre-PR checklist (reproduced from PATTERNS.md §11 — grade the diff against every line)

- [ ] `<PageHeader>` is the first child of the page wrapper.
- [ ] `breadcrumbs` is set (real hierarchy, not just the page name).
- [ ] No subtitle → search + action buttons go in `filterLeadingActions`.
- [ ] Compact-inline search (§2a) when paired with action buttons; full-width
      `search` prop (§2b) only when no buttons compete for the right side.
- [ ] Filters live in a `<FilterSheet>` (popup desktop / bottom sheet mobile)
      with pending state; not in an inline panel.
- [ ] List uses one of the three §4 patterns; nothing else.
- [ ] Row padding `py-3`. Stat-list (§4c) uses one column-header row + flat
      data rows with `md:contents` cells — never per-row labels above each
      value.
- [ ] Status indicators are `<Badge>` components. No ad-hoc dots/circles.
- [ ] Empty / loading / error states match §5 via `@/components/query` atoms;
      every list query renders an `isError` branch.
- [ ] Mutations go through `useApiMutation` with `invalidates`/
      `invalidatesGlobal` fragments from `keys.ts`; no raw `api.*` +
      `refetch()` substitute outside the documented pipeline exemption.
- [ ] Queries/mutations live in `src/hooks/queries/<domain>.ts` with
      co-located response types; key fragments in `keys.ts`. No inline
      `useApiQuery`/`useApiMutation` in page files.
- [ ] Action buttons follow the §7 variant/size table.
- [ ] Colors are from §12 — no purple/violet/fuchsia/pink/indigo; no raw hex;
      no arbitrary Tailwind values.
- [ ] The reviewer/author read the 3 anchor pages (DocumentsPage,
      PurchasesPage, BankStatementsPage) before deciding anything novel.
