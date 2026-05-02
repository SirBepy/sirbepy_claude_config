$inputJson = [Console]::In.ReadToEnd()
try {
    $j = $inputJson | ConvertFrom-Json
    $cmd = $j.tool_input.command
    if ($cmd -and $cmd -match 'rename-session\.ps1') {
        $out = @{
            hookSpecificOutput = @{
                hookEventName = 'PreToolUse'
                permissionDecision = 'allow'
                permissionDecisionReason = 'Auto-approved: /close rename helper'
            }
        } | ConvertTo-Json -Compress -Depth 4
        [Console]::Out.Write($out)
    }
} catch {}
exit 0
