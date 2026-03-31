param(
  [string]$HealthUrl = "http://127.0.0.1:44777/health"
)

. (Join-Path $PSScriptRoot "bridge-common.ps1")

$tokenFile = Get-BridgeTokenFile
$extensionPath = Get-BridgeExtensionPath

Write-Host ""
Write-Host "Status da Actuar Bridge" -ForegroundColor Cyan
Write-Host "Token salvo: $(if (Test-Path $tokenFile) { 'sim' } else { 'nao' })"
Write-Host "Arquivo token: $tokenFile"
Write-Host "Pasta extensao: $extensionPath"
Write-Host ""

try {
  $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 3
  Write-Host "Bridge local: ONLINE" -ForegroundColor Green
  Write-Host "Aba anexada: $($response.browser_attached)"
  Write-Host "Titulo aba: $($response.browser_title)"
  Write-Host "URL aba: $($response.browser_url)"
  Write-Host "Job pendente: $($response.pending_job_id)"
  Write-Host "Ultimo erro: $($response.last_error)"
}
catch {
  Write-Host "Bridge local: OFFLINE" -ForegroundColor Yellow
  Write-Host "Se a janela da bridge nao estiver aberta, rode 2-iniciar-bridge.cmd."
}
