# Dot-sourced by claim-todo.ps1 and complete-todo.ps1. Not a module - these scripts
# are invoked directly by path, matching this tree's convention.

# Resolves a raw todo id (or full "<id>-<slug>" stem) to a backlog file, falling back
# to an exact "<stem>.md" match for a prefix-less filename (malformed per
# ai-todos-format.md but still archivable). Returns the matched pattern so
# complete-todo.ps1 can reuse it for its second, done\ search.
function Resolve-TodoFile {
    param(
        [Parameter(Mandatory = $true)][string]$Dir,
        [Parameter(Mandatory = $true)][string]$RawId,
        [string]$Slug
    )

    $numericId = $RawId
    $slugLocal = $Slug
    if ($RawId -match '^0*(\d+)-(.+)$') {
        $numericId = $matches[1]
        if (-not $slugLocal) { $slugLocal = $matches[2] }
    }

    $idPattern = "^0*$([regex]::Escape($numericId))-.*\.md$"
    $pattern = $idPattern
    $allFiles = Get-ChildItem -Path $Dir -Filter '*.md' -File -ErrorAction SilentlyContinue
    $matchesFound = $allFiles | Where-Object { $_.Name -match $idPattern }

    $fellBack = $false
    if ($numericId -notmatch '^\d+$') {
        # Prefix-less id: the returned Pattern always takes this stem shape, even
        # when nothing matches in $Dir right now, so a caller reusing Pattern
        # against a second directory (done\, once the file has been archived)
        # still finds it instead of falling through to the digit-prefixed shape.
        $stemPattern = "^$([regex]::Escape($numericId))\.md$"
        $pattern = $stemPattern
        if (@($matchesFound).Count -eq 0) {
            $stemMatches = $allFiles | Where-Object { $_.Name -match $stemPattern }
            if (@($stemMatches).Count -gt 0) {
                $matchesFound = $stemMatches
                $slugLocal = $null
                $fellBack = $true
            }
        }
    }

    [ordered]@{
        NumericId = $numericId
        Slug      = $slugLocal
        Pattern   = $pattern
        Matches   = $matchesFound
        FellBack  = $fellBack
    }
}
