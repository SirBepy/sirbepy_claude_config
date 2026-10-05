# Lens pack: React + TanStack Query

Append these under the matching generic lens in `rubric-template.md`. Targets a
React SPA using TanStack Query (React Query) for server-state - the fibo
frontend2 audit (2026-10-01/03) hand-built an equivalent rubric for exactly this
stack; this pack is the reusable version so the next React/TanStack repo doesn't
need one rewritten from scratch.

## Architecture & code health
- Query-key duplication: the same resource's key built by hand in more than one
  component/hook instead of a shared key factory - these drift and silently stop
  invalidating each other.
- A component reaching into another feature's query cache directly (`queryClient.getQueryData`
  on a key it doesn't own) instead of importing that feature's own hook.
- Prop-drilling more than two levels where context or a colocated query hook would
  remove it - only a finding when it's actually causing duplicated fetch logic,
  not as a style preference.
- Fetch logic hand-rolled with `useEffect` + `useState` where a `useQuery` already
  exists for the same resource elsewhere in the codebase.

## Robustness & failure modes
- Stale-while-revalidate bugs: a mutation that doesn't invalidate or optimistically
  update every query key that should change as a result - check `onSuccess`/
  `onSettled` against every reader of that data, not just the obvious one.
- Missing `staleTime`/`gcTime` tuning on a query that's fetched on every
  navigation when the data rarely changes - a real idle-cost finding, not a nit,
  if it's hitting the network on a hot path.
- A query with no `enabled` guard that fires with an undefined/null required
  parameter (a race on first render before auth/user id is ready).
- An infinite query (`useInfiniteQuery`) with no cap on accumulated pages -
  unbounded memory growth on a long scroll session.
- Error boundaries: does a query error actually surface to the user, or does an
  unhandled rejection get swallowed by a missing `onError`/error UI.
- Suspense boundaries (if used): is there a boundary between every
  `useSuspenseQuery` and the nearest interactive ancestor, or does one slow query
  blank the whole page.

## Security & trust surface
- Any query result containing another user's data cached under a key that
  doesn't include the current user/tenant id - a cache collision across an
  account switch.
- A mutation that trusts a client-supplied id/role instead of deriving it from
  the authenticated session server-side.

## Product & UX
- Loading state: does every `isLoading`/`isPending` path show feedback, or does
  a slow query render a blank/undefined-shaped UI.
- Does a failed mutation roll back an optimistic update cleanly, or does the UI
  show a success state that the server then silently rejected.
