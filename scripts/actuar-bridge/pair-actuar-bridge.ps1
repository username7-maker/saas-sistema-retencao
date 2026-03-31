param(
  [string]$ApiBaseUrl = "https://ai-gym-os-api-production.up.railway.app",
  [string]$DeviceName = "",
  [string]$PairingCode = ""
)

. (Join-Path $PSScriptRoot "bridge-common.ps1")

$workspaceRoot = Get-BridgeWorkspaceRoot
$tokenFile = Get-BridgeTokenFile
$tokenDir = Split-Path $tokenFile -Parent

if (-not $DeviceName) {
  $DeviceName = if ($env:COMPUTERNAME) { "Bridge $($env:COMPUTERNAME)" } else { "Bridge Academia" }
}

if (-not $PairingCode) {
  $PairingCode = Read-Host "Cole o codigo de pareamento do AI GYM OS"
}

if (-not $PairingCode) {
  throw "Codigo de pareamento obrigatorio."
}

New-Item -ItemType Directory -Force -Path $tokenDir | Out-Null

Write-Host ""
Write-Host "Pareando bridge local..." -ForegroundColor Cyan
Write-Host "API: $ApiBaseUrl"
Write-Host "Estacao: $DeviceName"
Write-Host "Token: $tokenFile"
Write-Host ""

Push-Location $workspaceRoot
try {
  Ensure-BridgeDependencies
  $exitCode = Invoke-BridgePythonModule -Arguments @(
    "-m", "actuar_bridge.main",
    "pair",
    "--api-base-url", $ApiBaseUrl,
    "--pairing-code", $PairingCode,
    "--device-name", $DeviceName,
    "--token-file", $tokenFile
  )
  if ($exitCode -ne 0) {
    exit $exitCode
  }
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Pareamento concluido." -ForegroundColor Green
Write-Host "Proximo passo: rode 2-iniciar-bridge.cmd e deixe a janela aberta."
