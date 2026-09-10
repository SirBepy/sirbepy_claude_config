<#
.SYNOPSIS
  Scratch-repo regression test for archive-batch.ps1's pathspec (todo 932: a tracked
  source's deletion silently missing from .Pathspec because Test-Path on it is always
  false after Move-Item already ran).

.DESCRIPTION
  Not wired into ci/run_all.py (that file is off limits to this change) - run by hand:
    powershell -File skills/mega-todos/test-archive-batch.ps1
  Exits 0 on pass, 1 on any failed assertion. Every scratch directory it creates is
  removed in a finally block; failures print but never stop cleanup.

  Two scenarios:
    1. Current code (this file's sibling archive-batch.ps1) against a fresh scratch
       repo with one TRACKED todo (id 100) and one UNTRACKED todo (id 200, the todo-848
       shape). Asserts the tracked source's deletion IS in .Pathspec, the untracked
       source stays OUT, and a pathspec commit built from .Pathspec leaves no stray
       ` D` in `git status --porcelain`.
    2. The pre-fix code, read from this repo's own HEAD (git show, never git checkout -
       nothing here mutates the real working tree) and replayed against a second
       scratch repo with the same tracked todo, to show the bug this fix closes: the
       tracked source is missing from .Pathspec and a stray ` D` survives the commit.
#>
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
    if ($Condition) { Write-Host "  PASS: $Message" }
    else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

function New-ScratchRepo([string]$Path) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    git -c init.defaultBranch=main init -q $Path
    git -C $Path config user.email "test@example.com"
    git -C $Path config user.name "archive-batch test"

    $todosDir = Join-Path $Path '.claude\todos'
    New-Item -ItemType Directory -Path $todosDir -Force | Out-Null

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $trackedPath = Join-Path $todosDir '100-tracked-todo.md'
    [System.IO.File]::WriteAllText($trackedPath, "# Tracked todo`r`n`r`n## Acceptance`r`n`r`n- done`r`n", $utf8NoBom)
    $untrackedPath = Join-Path $todosDir '200-untracked-todo.md'
    [System.IO.File]::WriteAllText($untrackedPath, "# Untracked todo`r`n`r`n## Acceptance`r`n`r`n- done`r`n", $utf8NoBom)

    git -C $Path add -- '.claude/todos/100-tracked-todo.md'
    git -C $Path commit -q -m "seed tracked todo"
    # 200-untracked-todo.md deliberately NOT added - mirrors the untracked-source
    # shape from todo 848 that must stay excluded from the pathspec.

    [PSCustomObject]@{
        Root       = $Path
        TodosDir   = $todosDir
        Tracked    = $trackedPath
        Untracked  = $untrackedPath
    }
}

$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$stamp = [guid]::NewGuid().ToString('N').Substring(0, 8)
$scratchNew = Join-Path $env:TEMP "archive-batch-test-new-$stamp"
$scratchOldData = Join-Path $env:TEMP "archive-batch-test-olddata-$stamp"
$scratchOldCode = Join-Path $env:TEMP "archive-batch-test-oldcode-$stamp"

try {
    # --- Scenario 1: current (fixed) code ---
    Write-Host "=== Scenario 1: current archive-batch.ps1 ==="
    $seed = New-ScratchRepo -Path $scratchNew
    $scriptPath = Join-Path $PSScriptRoot 'archive-batch.ps1'

    $result = & $scriptPath -Items "100|closed in test", "200|closed in test" -RepoRoot $seed.Root

    Assert ($result.Failures.Count -eq 0) "zero archive failures (got: $($result.Failures -join '; '))"

    $doneTracked = Join-Path $seed.TodosDir 'done\100-tracked-todo.md'
    $doneUntracked = Join-Path $seed.TodosDir 'done\200-untracked-todo.md'

    Assert ($result.Pathspec -contains $seed.Tracked) "tracked source '$($seed.Tracked)' IS in .Pathspec (todo 932 fix)"
    Assert ($result.Pathspec -contains $doneTracked) "tracked dest '$doneTracked' is in .Pathspec"
    Assert (-not ($result.Pathspec -contains $seed.Untracked)) "untracked source stays OUT of .Pathspec (todo 848 preserved)"
    Assert ($result.Pathspec -contains $doneUntracked) "untracked dest '$doneUntracked' is in .Pathspec"

    # A pathspec commit needs an explicit `git add` for paths git doesn't know yet
    # (commit/SKILL.md step 7's documented exception) - both done\ destinations here.
    # The tracked source needs none: `git commit -- <pathspec>` records a tracked
    # path's current working-tree state, deletion included, with no `git add`/`git rm`.
    git -C $seed.Root add -- $doneTracked $doneUntracked
    git -C $seed.Root commit -q -m "archive batch" -- $result.Pathspec

    $statusAfter = git -C $seed.Root status --porcelain
    $strayDeletes = $statusAfter | Where-Object { $_ -match '^\s*D\s' }
    Assert ($strayDeletes.Count -eq 0) "no stray staged/unstaged deletion after commit (found: $($strayDeletes -join '; '))"

    # git compresses a same-content move into a single "{ => done}" rename line
    # rather than separate add/delete lines - --no-renames forces it back apart
    # so the assertion can see both paths named explicitly.
    $statOutput = (git -C $seed.Root show --stat --no-renames HEAD | Out-String)
    Assert ($statOutput -match [regex]::Escape('.claude/todos/100-tracked-todo.md') -and $statOutput -match [regex]::Escape('.claude/todos/done/100-tracked-todo.md')) "HEAD's stat names both halves of the tracked move"

    Write-Host "--- git status --porcelain (scenario 1, after commit) ---"
    if ($statusAfter) { $statusAfter | ForEach-Object { Write-Host "  $_" } } else { Write-Host "  (clean)" }
    Write-Host "--- git show --stat HEAD (scenario 1) ---"
    Write-Host $statOutput

    # --- Scenario 2: pre-fix code, replayed from this repo's own HEAD ---
    Write-Host "=== Scenario 2: pre-fix archive-batch.ps1 (git show HEAD, no checkout) ==="
    $oldContent = (git -C $repoRoot show 'HEAD:skills/mega-todos/archive-batch.ps1' | Out-String)
    if (-not $oldContent.Trim()) {
        throw "could not read HEAD:skills/mega-todos/archive-batch.ps1 - is this repo's HEAD missing the file?"
    }

    $oldSkillsRoot = Join-Path $scratchOldCode 'skills'
    New-Item -ItemType Directory -Path (Join-Path $oldSkillsRoot 'mega-todos') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $oldSkillsRoot 'close') -Force | Out-Null
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $oldScriptPath = Join-Path $oldSkillsRoot 'mega-todos\archive-batch.ps1'
    [System.IO.File]::WriteAllText($oldScriptPath, $oldContent, $utf8NoBom)
    # Real close/_shared.ps1 and close/complete-todo.ps1 are off limits to EDIT, not to
    # READ - the old script dot-sources/calls them by relative path, so an unmodified
    # copy has to sit next to the replayed script for that resolution to work at all.
    Copy-Item (Join-Path $repoRoot 'skills\close\_shared.ps1') (Join-Path $oldSkillsRoot 'close\_shared.ps1')
    Copy-Item (Join-Path $repoRoot 'skills\close\complete-todo.ps1') (Join-Path $oldSkillsRoot 'close\complete-todo.ps1')

    $seedOld = New-ScratchRepo -Path $scratchOldData
    $oldResult = & $oldScriptPath -Items "100|closed in test" -RepoRoot $seedOld.Root

    $oldDoneTracked = Join-Path $seedOld.TodosDir 'done\100-tracked-todo.md'
    Assert (-not ($oldResult.Pathspec -contains $seedOld.Tracked)) "pre-fix .Pathspec OMITS the tracked source (reproduces todo 932)"
    Assert ($oldResult.Pathspec -contains $oldDoneTracked) "pre-fix .Pathspec still has the dest half"

    git -C $seedOld.Root add -- $oldDoneTracked
    git -C $seedOld.Root commit -q -m "archive batch (pre-fix pathspec)" -- $oldResult.Pathspec

    $oldStatusAfter = git -C $seedOld.Root status --porcelain
    $oldStrayDeletes = $oldStatusAfter | Where-Object { $_ -match '^\s*D\s' }
    Assert ($oldStrayDeletes.Count -gt 0) "pre-fix code leaves a stray staged deletion behind (the bug todo 932 reports)"

    Write-Host "--- git status --porcelain (scenario 2, pre-fix, after commit) ---"
    if ($oldStatusAfter) { $oldStatusAfter | ForEach-Object { Write-Host "  $_" } } else { Write-Host "  (clean)" }
}
finally {
    foreach ($p in @($scratchNew, $scratchOldData, $scratchOldCode)) {
        if (Test-Path $p) { Remove-Item -Path $p -Recurse -Force }
    }
    $stillThere = @($scratchNew, $scratchOldData, $scratchOldCode) | Where-Object { Test-Path $_ }
    if ($stillThere) {
        Write-Warning "scratch dirs still present after cleanup: $($stillThere -join ', ')"
    }
    else {
        Write-Host "scratch cleanup verified: $scratchNew, $scratchOldData, $scratchOldCode all removed"
    }
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "FAIL: $($failures.Count) assertion(s) failed:"
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host ""
Write-Host "OK: all assertions passed"
exit 0
