param(
  [string]$ApiBaseUrl = "https://ai-gym-os-api-production.up.railway.app",
  [string]$DeviceName = ""
)

. (Join-Path $PSScriptRoot "bridge-common.ps1")

$tokenFile = Get-BridgeTokenFile
$pairScript = Join-Path $PSScriptRoot "pair-actuar-bridge.ps1"
$launchScript = Join-Path $PSScriptRoot "launch-actuar-workstation.ps1"

if (-not (Test-Path $tokenFile)) {
  & $pairScript -ApiBaseUrl $ApiBaseUrl -DeviceName $DeviceName
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
else {
  Write-Host ""
  Write-Host "Bridge ja pareada. Reaproveitando token existente." -ForegroundColor Yellow
}

& $launchScript -ApiBaseUrl $ApiBaseUrl
exit $LASTEXITCODE
