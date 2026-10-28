<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Make Get-SentryIssue.ps1 accept ZNG-APP-xx short ids

**Type:** skill-improvement

## Goal

Let `Get-SentryIssue.ps1` take the short id Joe actually copies out of the Sentry issue stream,
instead of failing and forcing a manual API round-trip first.

## Context

`C:\Users\tecno\.claude\scripts\Get-SentryIssue.ps1` (used by the `/sentry` skill at
`C:\Users\tecno\.claude-personal\skills\sentry\SKILL.md`) parses its `UrlOrId` argument at lines
52-62 and accepts only:

- a bare numeric id (`^\d+$`), or
- a full `https://<org>.sentry.io/.../issues/<numeric>/` URL.

Anything else hits `Write-Error "Could not parse URL or issue ID from: $UrlOrId"` and exits 1.

Joe pastes short ids (`ZNG-APP-9W`, `ZNG-APP-9Y`) because that is what the issue stream displays.
On 2026-08-03 three such calls failed at the start of a triage session before the short ids were
resolved by hand via the Sentry API. The `/sentry` skill's own drill-in section tells the model to
run the script with `<id>`, which reads as though short ids work.

## Approach

In the argument-parsing block at `Get-SentryIssue.ps1:52-62`, add a branch for the short-id shape
(`^[A-Z0-9-]+-[A-Z0-9]+$`, i.e. anything non-numeric that is not a URL) that resolves it first:

```powershell
$r = Invoke-RestMethod -Uri "$base/organizations/$Org/shortids/$UrlOrId/" -Headers $headers
$issueId = $r.groupId
```

That endpoint is confirmed working against `zirtue-nk` (2026-08-03). It needs `-Org`, so keep the
existing "Org slug required when passing bare ID" guard applying to this branch too. The `$headers`
and `$base` variables are currently defined below the parse block, so either move them up or inline
the call after they exist.

Also update the `.PARAMETER UrlOrId` help text and the `.EXAMPLE` block at the top of the script to
show the short-id form, and mention it in the `/sentry` skill's Drill-in section.

## Acceptance

- `& Get-SentryIssue.ps1 ZNG-APP-9W -Org zirtue-nk` returns the same output as passing that issue's
  numeric id.
- Numeric ids and full URLs still work unchanged.
- An unparseable argument still errors clearly rather than making a doomed API call.

## Notes

Related memory: [[sentry-triage-zng-app]] documents the manual workaround, and should be trimmed
once this lands so it does not describe a limitation that no longer exists.
- Shipped 2026-08-11. Get-SentryIssue.ps1 now accepts ZNG-APP-xx short ids directly, verified live (ZNG-APP-6X resolved to issue 7325907587). Skill doc updated in commit 96cf0f9. NOTE: scripts/ is gitignored, so the script change itself is on disk only, not in git history.
