$ErrorActionPreference = "Continue"

$KeyPath = "C:\Users\HOME\.ssh\codex_raspberry_pi_ed25519"
$Remote = "user@172.30.1.8"
$Forward = "127.0.0.1:11434:127.0.0.1:11434"

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
