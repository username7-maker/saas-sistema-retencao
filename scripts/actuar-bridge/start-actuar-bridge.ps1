param(
  [string]$ApiBaseUrl = "https://ai-gym-os-api-production.up.railway.app",
  [ValidateSet("extension-relay", "attached-browser", "dry-run")]
  [string]$Mode = "extension-relay"
)

. (Join-Path $PSScriptRoot "bridge-common.ps1")

$workspaceRoot = Get-BridgeWorkspaceRoot
$tokenFile = Get-BridgeTokenFile

if (-not (Test-Path $tokenFile)) {
  throw "Bridge ainda nao pareada. Rode 1-parear-bridge.cmd primeiro."
}

Write-Host ""
Write-Host "Iniciando bridge local do Actuar..." -ForegroundColor Cyan
Write-Host "API: $ApiBaseUrl"
Write-Host "Modo: $Mode"
Write-Host "Token: $tokenFile"
Write-Host ""

if ($Mode -eq "extension-relay") {
  Write-Host "Checklist rapido:" -ForegroundColor Yellow
  Write-Host "1. Abra o Actuar no navegador."
  Write-Host "2. Clique em 'Anexar aba atual' na extensao."
  Write-Host "3. Deixe esta janela aberta durante o uso."
  Write-Host ""
}

Push-Location $workspaceRoot
try {
  Ensure-BridgeDependencies
  $arguments = @(
    "-m", "actuar_bridge.main",
    "run",
    "--api-base-url", $ApiBaseUrl,
    "--mode", $Mode,
    "--token-file", $tokenFile
  )

  if ($Mode -eq "extension-relay") {
    $arguments += @("--listen-host", "127.0.0.1", "--listen-port", "44777")
  }

  $exitCode = Invoke-BridgePythonModule -Arguments $arguments
  if ($exitCode -ne 0) {
    exit $exitCode
  }
}
finally {
  Pop-Location
}
