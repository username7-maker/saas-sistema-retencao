function Get-BridgeRepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-BridgeWorkspaceRoot {
  return (Get-BridgeRepoRoot)
}

function Get-BridgeEvidenceRoot {
  $workspaceRoot = Split-Path (Get-BridgeRepoRoot) -Parent
  return (Join-Path $workspaceRoot "actuar-evidence")
}

function Get-BridgeTokenFile {
  return (Join-Path (Get-BridgeEvidenceRoot) ".actuar-bridge-token.json")
}

function Get-BridgeExtensionPath {
  return (Join-Path (Get-BridgeRepoRoot) "actuar_bridge_extension")
}

function Get-BridgeBrowserProfileDir {
  return (Join-Path (Get-BridgeEvidenceRoot) "browser-profile")
}

function Get-BridgeBrowserExecutable {
  $candidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  throw "Chrome ou Edge nao encontrado. Instale um desses navegadores no PC da academia."
}

function Test-BridgeOnline {
  param(
    [string]$HealthUrl = "http://127.0.0.1:44777/health"
  )

  try {
    $null = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2
    return $true
  }
  catch {
    return $false
  }
}

function Invoke-BridgePythonModule {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Arguments
  )

  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    & $pyLauncher.Source -3 @Arguments
    return
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    & $python.Source @Arguments
    return
  }

  throw "Python 3 nao encontrado. Instale Python ou use o launcher 'py'."
}

function Test-BridgePythonImport {
  param(
    [Parameter(Mandatory = $true)]
    [string]$ImportName
  )

  Invoke-BridgePythonModule -Arguments @("-c", "import $ImportName")
  return $LASTEXITCODE -eq 0
}

function Install-BridgePythonPackage {
  param(
    [Parameter(Mandatory = $true)]
    [string]$PackageName
  )

  Write-Host "Instalando dependencia Python: $PackageName" -ForegroundColor Yellow
  Invoke-BridgePythonModule -Arguments @("-m", "pip", "install", $PackageName)
  if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar a dependencia Python: $PackageName"
  }
}

function Ensure-BridgeDependencies {
  if (-not (Test-BridgePythonImport -ImportName "httpx")) {
    Install-BridgePythonPackage -PackageName "httpx"
  }
}
