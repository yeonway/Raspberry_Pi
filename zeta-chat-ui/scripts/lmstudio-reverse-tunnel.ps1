$ErrorActionPreference = "Continue"

$KeyPath = "C:\Users\HOME\.ssh\codex_raspberry_pi_ed25519"
$Remote = "user@172.30.1.8"
$Forward = "127.0.0.1:1234:127.0.0.1:1235"
$ProjectDir = "C:\Users\HOME\Desktop\Raspberry_Pi\zeta-chat-ui"
$ProxyScript = Join-Path $ProjectDir "scripts\lmstudio-logging-proxy.cjs"

$proxy = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -eq "node.exe" -and $_.CommandLine -like "*lmstudio-logging-proxy.cjs*"
  }

if (-not $proxy) {
  Start-Process `
    -FilePath "node" `
    -ArgumentList $ProxyScript `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden
  Start-Sleep -Seconds 1
}

while ($true) {
  & ssh `
    -i $KeyPath `
    -o IdentitiesOnly=yes `
    -o ExitOnForwardFailure=yes `
    -o ServerAliveInterval=30 `
    -o ServerAliveCountMax=3 `
    -N `
    -R $Forward `
    $Remote

  Start-Sleep -Seconds 5
}
