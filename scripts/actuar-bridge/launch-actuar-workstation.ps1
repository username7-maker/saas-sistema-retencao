param(
  [string]$ActuarUrl = "https://app.actuar.com/",
  [string]$ApiBaseUrl = "https://ai-gym-os-api-production.up.railway.app"
)

. (Join-Path $PSScriptRoot "bridge-common.ps1")

$tokenFile = Get-BridgeTokenFile
if (-not (Test-Path $tokenFile)) {
  throw "Bridge ainda nao pareada. Rode 0-primeiro-uso-academia.cmd primeiro."
}

$browserPath = Get-BridgeBrowserExecutable
$extensionPath = Get-BridgeExtensionPath
$profileDir = Get-BridgeBrowserProfileDir
$startScript = Join-Path $PSScriptRoot "start-actuar-bridge.ps1"

New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

if (-not (Test-BridgeOnline)) {
  Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $startScript,
    "-ApiBaseUrl", $ApiBaseUrl,
    "-Mode", "extension-relay"
  )
  Start-Sleep -Seconds 2
}

Start-Process -FilePath $browserPath -ArgumentList @(
  "--new-window",
  "--no-first-run",
  "--user-data-dir=$profileDir",
  "--load-extension=$extensionPath",
  $ActuarUrl
)

Write-Host ""
Write-Host "Modo academia iniciado." -ForegroundColor Green
Write-Host "1. Use a janela do navegador aberta por este atalho."
Write-Host "2. Faca login no Actuar, se necessario."
Write-Host "3. A extensao deve se anexar automaticamente a primeira aba do Actuar."
Write-Host "4. Deixe a janela da bridge aberta durante o uso."
