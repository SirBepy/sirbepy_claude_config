param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('devices','wait-boot','screenshot','tap','tap-and-capture','clear-field','type-field','dismiss-keyboard','install','record-motion')]
    [string]$Action,

    [string]$Serial,
    [string]$Out,
    [string]$RefShot,
    [int]$X,
    [int]$Y,
    [string]$Text,
    [int]$TimeoutSec = 90,
    [int]$WaitMs = 800,
    [string]$Apk,
    [string]$Steps,
    [string]$Strips,
    [int]$TimeLimit = 16
)

# On disk rather than inline in SKILL.md: keeps the screencap/pull/rm two-step and the
# png-vs-wm coordinate math in one tested place instead of hand-typed per call.

$ErrorActionPreference = 'Stop'

function Resolve-Serial {
    param([string]$Serial)
    if ($Serial) { return $Serial }
    $lines = & adb devices | Select-String "`tdevice$"
    $ids = $lines | ForEach-Object { ($_ -split "`t")[0] }
    if ($ids.Count -eq 0) { throw "No adb devices attached. Run 'adb devices' to check." }
    if ($ids.Count -gt 1) { throw "Multiple devices attached ($($ids -join ', ')). Pass -Serial explicitly - never let adb pick." }
    return $ids[0]
}

function Get-WmSize {
    # Override size (if set) is the space `input tap` expects; screencap always captures physical.
    param([string]$Serial)
    $lines = & adb -s $Serial shell wm size
    $override = $lines | Select-String 'Override size:\s*(\d+)x(\d+)'
    $physical = $lines | Select-String 'Physical size:\s*(\d+)x(\d+)'
    $m = if ($override) { $override } else { $physical }
    if (-not $m) { throw "Could not parse 'wm size' output: $lines" }
    [pscustomobject]@{
        Width  = [int]$m.Matches[0].Groups[1].Value
        Height = [int]$m.Matches[0].Groups[2].Value
    }
}

function Get-PngSize {
    param([string]$Path)
    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile((Resolve-Path $Path))
    $size = [pscustomobject]@{ Width = $img.Width; Height = $img.Height }
    $img.Dispose()
    return $size
}

function Get-DefaultScreenshotPath {
    $renameScript = Join-Path $PSScriptRoot '..\close\rename-session.ps1'
    $id = & $renameScript -GetId
    $dir = ".for_bepy/screenshots/$id"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Join-Path $dir "adb-$(Get-Date -Format 'HHmmss-fff').png"
}

function Get-DefaultRecordingPath {
    param([string]$Ext)
    $renameScript = Join-Path $PSScriptRoot '..\close\rename-session.ps1'
    $id = & $renameScript -GetId
    $dir = ".for_bepy/screenshots/$id"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Join-Path $dir "adb-$(Get-Date -Format 'HHmmss-fff').$Ext"
}

function Resolve-Ffmpeg {
    # Guard: record-motion must still pull the mp4 and say so when ffmpeg isn't present,
    # rather than throwing partway through and losing the recording.
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $scoopShim = 'C:\Users\tecno\scoop\shims\ffmpeg.exe'
    if (Test-Path $scoopShim) { return $scoopShim }
    return $null
}

function ConvertTo-DeviceShellSteps {
    # Translates -Steps (tap/wait/key tokens, tap coords in the PNG space the caller read
    # off a screenshot) into device shell commands, scaling tap coords the same way
    # Convert-TapCoords does for the `tap` action - raw `input tap` at unscaled PNG
    # coordinates misses the target widget on any device where PNG size != wm size.
    param([string]$Steps, [double]$ScaleX, [double]$ScaleY)
    $parts = @()
    foreach ($tok in ($Steps -split ';')) {
        $tok = $tok.Trim()
        if (-not $tok) { continue }
        $kv = $tok -split ':', 2
        $kind = $kv[0].Trim().ToLowerInvariant()
        $arg = if ($kv.Count -gt 1) { $kv[1].Trim() } else { '' }
        switch ($kind) {
            'tap' {
                $xy = $arg -split ','
                $pngX = [int]$xy[0].Trim()
                $pngY = [int]$xy[1].Trim()
                $devX = [math]::Round($pngX / $ScaleX)
                $devY = [math]::Round($pngY / $ScaleY)
                $parts += "input tap $devX $devY"
            }
            'wait' {
                $secs = [int]$arg / 1000.0
                $secsStr = [string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{0:0.###}', $secs)
                $parts += "sleep $secsStr"
            }
            'key' {
                $parts += "input keyevent $arg"
            }
            default { throw "Unknown step kind '$kind' in -Steps (expected tap:X,Y / wait:MS / key:CODE)" }
        }
    }
    return $parts
}

function Take-Screenshot {
    # Two-step screencap+pull, never a shell `>` redirect - that corrupts the PNG
    # (text-mode CRLF translation over the binary stream).
    param([string]$Serial, [string]$LocalPath)
    $remote = '/sdcard/_adb_drive_tmp.png'
    & adb -s $Serial shell screencap -p $remote | Out-Null
    $dir = Split-Path -Parent $LocalPath
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    & adb -s $Serial pull $remote $LocalPath | Out-Null
    & adb -s $Serial shell rm $remote | Out-Null
    return $LocalPath
}

function Get-OrientationInfo {
    # Pure/testable: a rotated device leaves `wm size` reporting the pre-rotation resolution
    # while screencap already reflects the rotated frame, so PNG and wm size swap W/H exactly.
    # When that exact swap is detected, `input tap` is already operating in the screenshot's own
    # space, so the correct conversion is 1:1, not the axis-crossed ratios wm-based scaling gives.
    param([int]$PngWidth, [int]$PngHeight, [int]$WmWidth, [int]$WmHeight)
    $orientation = if ($PngWidth -gt $PngHeight) { 'landscape' } else { 'portrait' }
    $rotated = ($PngWidth -eq $WmHeight) -and ($PngHeight -eq $WmWidth) -and ($PngWidth -ne $WmWidth)
    if ($rotated) {
        [pscustomobject]@{ Orientation = $orientation; Rotated = $true; ScaleX = 1.0; ScaleY = 1.0 }
    } else {
        [pscustomobject]@{ Orientation = $orientation; Rotated = $false; ScaleX = ($PngWidth / $WmWidth); ScaleY = ($PngHeight / $WmHeight) }
    }
}

function Convert-TapCoords {
    # X/Y are in the pixel space of the screenshot the caller actually read (RefShot),
    # converted into the space `input tap` expects (wm size), not assumed to match.
    param([string]$Serial, [int]$PngX, [int]$PngY, [string]$ScreenshotPath)
    $png = Get-PngSize -Path $ScreenshotPath
    $wm  = Get-WmSize -Serial $Serial
    $info = Get-OrientationInfo -PngWidth $png.Width -PngHeight $png.Height -WmWidth $wm.Width -WmHeight $wm.Height
    [pscustomobject]@{
        X = [math]::Round($PngX / $info.ScaleX)
        Y = [math]::Round($PngY / $info.ScaleY)
        Orientation = $info.Orientation
        Rotated = $info.Rotated
    }
}

switch ($Action) {
    'devices' {
        & adb devices -l
    }

    'wait-boot' {
        $s = Resolve-Serial -Serial $Serial
        & adb -s $s wait-for-device
        $deadline = (Get-Date).AddSeconds($TimeoutSec)
        do {
            $val = (& adb -s $s shell getprop sys.boot_completed).Trim()
            if ($val -eq '1') { Write-Output "boot_completed serial=$s"; exit 0 }
            Start-Sleep -Seconds 2
        } while ((Get-Date) -lt $deadline)
        throw "Timed out after ${TimeoutSec}s waiting for boot on $s"
    }

    'screenshot' {
        $s = Resolve-Serial -Serial $Serial
        $path = if ($Out) { $Out } else { Get-DefaultScreenshotPath }
        Take-Screenshot -Serial $s -LocalPath $path | Out-Null
        $png = Get-PngSize -Path $path
        $wm  = Get-WmSize -Serial $s
        $info = Get-OrientationInfo -PngWidth $png.Width -PngHeight $png.Height -WmWidth $wm.Width -WmHeight $wm.Height
        Write-Output "path=$path pngSize=$($png.Width)x$($png.Height) wmSize=$($wm.Width)x$($wm.Height) orientation=$($info.Orientation) rotated=$($info.Rotated) scaleX=$([math]::Round($info.ScaleX,3)) scaleY=$([math]::Round($info.ScaleY,3))"
    }

    'tap' {
        if (-not $RefShot) { throw "-RefShot is required: the screenshot path the X/Y were read from" }
        $s = Resolve-Serial -Serial $Serial
        $conv = Convert-TapCoords -Serial $s -PngX $X -PngY $Y -ScreenshotPath $RefShot
        & adb -s $s shell input tap $conv.X $conv.Y
        Write-Output "tapped serial=$s pngCoords=$X,$Y inputCoords=$($conv.X),$($conv.Y)"
    }

    'tap-and-capture' {
        if (-not $RefShot) { throw "-RefShot is required: the screenshot path the X/Y were read from" }
        $s = Resolve-Serial -Serial $Serial
        $conv = Convert-TapCoords -Serial $s -PngX $X -PngY $Y -ScreenshotPath $RefShot
        & adb -s $s shell input tap $conv.X $conv.Y
        Start-Sleep -Milliseconds $WaitMs
        $path = if ($Out) { $Out } else { Get-DefaultScreenshotPath }
        Take-Screenshot -Serial $s -LocalPath $path | Out-Null
        Write-Output "tapped serial=$s pngCoords=$X,$Y inputCoords=$($conv.X),$($conv.Y) after=$path"
    }

    'clear-field' {
        # 123 = move cursor to end, then 67 (backspace) x30 - clears regardless of stale length.
        $s = Resolve-Serial -Serial $Serial
        & adb -s $s shell input keyevent 123
        1..30 | ForEach-Object { & adb -s $s shell input keyevent 67 } | Out-Null
        Write-Output "cleared serial=$s"
    }

    'type-field' {
        if (-not $Text) { throw "-Text is required for type-field" }
        $s = Resolve-Serial -Serial $Serial
        & adb -s $s shell input keyevent 123
        1..30 | ForEach-Object { & adb -s $s shell input keyevent 67 } | Out-Null
        $escaped = $Text -replace ' ', '%s'
        & adb -s $s shell input text $escaped
        Write-Output "typed serial=$s text=$Text"
    }

    'dismiss-keyboard' {
        # keyevent 4 (back) only. NEVER 111 - that opens Gboard settings, not dismiss.
        $s = Resolve-Serial -Serial $Serial
        & adb -s $s shell input keyevent 4
        Write-Output "dismissed serial=$s"
    }

    'install' {
        if (-not $Apk) { throw "-Apk is required for install" }
        $s = Resolve-Serial -Serial $Serial
        & adb -s $s install -r $Apk
    }

    'record-motion' {
        if (-not $Steps) { throw "-Steps is required for record-motion, e.g. 'tap:76,153;wait:2500;key:4;wait:2000;tap:957,2088'" }
        $s = Resolve-Serial -Serial $Serial

        # Scale factor comes from the device's CURRENT screen, same source `tap` uses -
        # -Steps tap coords are PNG-space from a screenshot already read, not device-input
        # space, so they need the same PNG-size-vs-wm-size conversion before being baked
        # into the one device-side shell string below.
        $refShot = Join-Path ([System.IO.Path]::GetTempPath()) "adb-drive-record-ref-$PID.png"
        Take-Screenshot -Serial $s -LocalPath $refShot | Out-Null
        $png = Get-PngSize -Path $refShot
        $wm  = Get-WmSize -Serial $s
        $info = Get-OrientationInfo -PngWidth $png.Width -PngHeight $png.Height -WmWidth $wm.Width -WmHeight $wm.Height
        Remove-Item -Force $refShot -ErrorAction SilentlyContinue

        $deviceSteps = ConvertTo-DeviceShellSteps -Steps $Steps -ScaleX $info.ScaleX -ScaleY $info.ScaleY
        $remoteMp4 = '/sdcard/_adb_drive_record_tmp.mp4'
        # screenrecord and every tap/wait/key run inside ONE device-side shell string so
        # timing is accurate by construction - separate host-side `adb` round trips under
        # screenrecord load drift by seconds, landing taps late or dropping them entirely.
        # Trailing `wait` blocks this call until screenrecord's own --time-limit ends it,
        # so the file below is never pulled mid-recording.
        $shellCmd = "screenrecord --time-limit $TimeLimit $remoteMp4 & " + ($deviceSteps -join '; ') + '; wait'
        & adb -s $s shell $shellCmd | Out-Null

        $outPath = if ($Out) { $Out } else { Get-DefaultRecordingPath -Ext 'mp4' }
        $outDir = Split-Path -Parent $outPath
        if (-not $outDir) { $outDir = '.' }
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
        & adb -s $s pull $remoteMp4 $outPath | Out-Null
        & adb -s $s shell rm $remoteMp4 | Out-Null

        $ffmpegExe = Resolve-Ffmpeg
        if (-not $ffmpegExe) {
            Write-Output "recorded serial=$s out=$outPath orientation=$($info.Orientation) rotated=$($info.Rotated) contactSheet=skipped(ffmpeg-not-found) strips=skipped(ffmpeg-not-found)"
            break
        }

        $base = Join-Path $outDir ([System.IO.Path]::GetFileNameWithoutExtension($outPath))
        $contactSheet = "$base-contact.png"
        # ffmpeg writes its banner/progress to stderr even on success; with
        # $ErrorActionPreference='Stop' that turns into a terminating NativeCommandError
        # regardless of exit code, so it's relaxed to 'Continue' for just these calls.
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        # Whole-video contact sheet by default, not just the requested strips - this is what
        # actually diagnoses a botched drive at a glance instead of guessing at offsets.
        & $ffmpegExe -y -i $outPath -vf "fps=2,tile=8x4" -frames:v 1 $contactSheet 2>$null | Out-Null

        $stripPaths = @()
        if ($Strips) {
            $i = 0
            foreach ($t in ($Strips -split ',')) {
                $t = $t.Trim()
                if (-not $t) { continue }
                $i++
                $stripPath = "$base-strip$i.png"
                # -ss AFTER -i: placed before -i it snaps to the nearest keyframe, so two
                # different timestamps can silently return byte-identical strips.
                & $ffmpegExe -y -i $outPath -ss $t -t 0.4 -vf "fps=25,scale=200:-1,tile=10x1" -frames:v 1 $stripPath 2>$null | Out-Null
                $stripPaths += $stripPath
            }
        }
        $ErrorActionPreference = $prevEap

        Write-Output "recorded serial=$s out=$outPath orientation=$($info.Orientation) rotated=$($info.Rotated) contactSheet=$contactSheet strips=$($stripPaths -join ',')"
    }
}
