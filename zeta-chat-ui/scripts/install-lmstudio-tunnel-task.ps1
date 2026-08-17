$ErrorActionPreference = "Stop"

$TaskName = "Zeta LM Studio Reverse Tunnel"
$ProjectDir = "C:\Users\HOME\Desktop\Raspberry_Pi\zeta-chat-ui"
$TunnelScript = Join-Path $ProjectDir "scripts\lmstudio-reverse-tunnel.ps1"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path -LiteralPath $TunnelScript)) {
  throw "Tunnel script not found: $TunnelScript"
}

$Action = New-ScheduledTaskAction `
  -Execute $PowerShell `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TunnelScript`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit ([TimeSpan]::Zero) `
  -MultipleInstances IgnoreNew `
  -RestartCount 999 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -StartWhenAvailable

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Keeps the Zeta LM Studio reverse SSH tunnel connected to the Raspberry Pi." `
  -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName"
