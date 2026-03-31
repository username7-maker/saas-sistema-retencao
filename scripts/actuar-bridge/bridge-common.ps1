function Get-BridgeRepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-BridgeWorkspaceRoot {
  return (Get-BridgeRepoRoot)
}

function Get-BridgeTokenFile {
  $workspaceRoot = Split-Path (Get-BridgeRepoRoot) -Parent
  return (Join-Path $workspaceRoot "actuar-evidence\.actuar-bridge-token.json")
}

function Get-BridgeExtensionPath {
  return (Join-Path (Get-BridgeRepoRoot) "actuar_bridge_extension")
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
