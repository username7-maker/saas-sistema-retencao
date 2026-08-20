[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("all", "up", "audit", "quality", "report", "status", "down")]
    [string]$Command = "all"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version 2.0

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$AuditRoot = Join-Path $RepoRoot "audit"
$ComposeFile = Join-Path $AuditRoot "docker-compose.audit.yml"
$RuntimeBase = Join-Path $env:TEMP "cordex-gym-os-audit"
$EvidenceBase = Join-Path $env:LOCALAPPDATA "CordexGymOSAudit\evidence"
$StatePath = Join-Path $RuntimeBase "active.json"
$ReportPath = Join-Path $RepoRoot ("docs\audits\{0}-cordex-gym-os-safe-audit.md" -f (Get-Date -Format "yyyy-MM-dd"))

function Get-UtcTimestamp {
    return [DateTime]::UtcNow.ToString("o")
}
function New-RandomBase64Url([int]$ByteCount = 32) {
    $bytes = New-Object byte[] $ByteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function New-RandomHex([int]$ByteCount = 32) {
    $bytes = New-Object byte[] $ByteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")
}

function Get-FreeTcpPort {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port } finally { $listener.Stop() }
}

function Write-JsonFile([string]$Path, $Value) {
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Protect-SecretFile([string]$Path) {
    try {
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $acl.SetOwner($identity.User)
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity.User, "FullControl", "Allow")
        $acl.AddAccessRule($rule)
        Set-Acl -LiteralPath $Path -AclObject $acl
        return $true
    } catch {
        return $false
    }
}

function Assert-PathWithin([string]$Path, [string]$Parent) {
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
    $fullParent = [System.IO.Path]::GetFullPath($Parent).TrimEnd("\")
    if (-not $fullPath.StartsWith($fullParent + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Safety guard rejected path outside runtime base: $fullPath"
    }
}

function Read-State {
    if (-not (Test-Path -LiteralPath $StatePath)) { throw "No active audit sandbox state was found." }
    return Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
}

function Read-EnvValue([string]$EnvPath, [string]$Name) {
    $prefix = "$Name="
    $line = Get-Content -LiteralPath $EnvPath | Where-Object { $_.StartsWith($prefix) } | Select-Object -First 1
    if (-not $line) { throw "Runtime secret $Name is unavailable." }
    return $line.Substring($prefix.Length)
}

function Get-ComposePrefix($State) {
    return @(
        "compose",
        "--project-name", [string]$State.project_name,
        "--env-file", [string]$State.env_path,
        "--file", $ComposeFile
    )
}

function Invoke-Compose($State, [string[]]$Arguments, [switch]$AllowFailure) {
    $prefix = Get-ComposePrefix $State
    & docker @prefix @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "Docker Compose failed with exit code $exitCode."
    }
    return $exitCode
}

function Wait-Http([string]$Url, [int]$TimeoutSeconds = 150) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Timed out waiting for loopback service health."
}

function New-AuditState {
    if (Test-Path -LiteralPath $StatePath) {
        throw "An audit sandbox state already exists. Run audit\audit.cmd down first."
    }
    New-Item -ItemType Directory -Path $RuntimeBase -Force | Out-Null
    New-Item -ItemType Directory -Path $EvidenceBase -Force | Out-Null

    $runId = "{0}-{1}" -f ([DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")), (New-RandomHex 4)
    $projectName = "cordex-gym-audit-{0}" -f (New-RandomHex 5)
    $runtimeDir = Join-Path $RuntimeBase $runId
    $evidenceDir = Join-Path $EvidenceBase $runId
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null

    $backendPort = Get-FreeTcpPort
    do { $frontendPort = Get-FreeTcpPort } while ($frontendPort -eq $backendPort)
    $backendUrl = "http://127.0.0.1:$backendPort"
    $frontendUrl = "http://127.0.0.1:$frontendPort"
    $envPath = Join-Path $runtimeDir "audit-secrets.env"
    $envLines = @(
        "AUDIT_PROJECT_NAME=$projectName",
        "AUDIT_POSTGRES_PASSWORD=$(New-RandomBase64Url 32)",
        "AUDIT_JWT_SECRET=$(New-RandomBase64Url 48)",
        "AUDIT_CPF_KEY=$(New-RandomHex 32)",
        "AUDIT_ACCOUNT_PASSWORD=$(New-RandomBase64Url 36)",
        "AUDIT_RESET_TOKEN=$(New-RandomBase64Url 40)",
        "AUDIT_BACKEND_PORT=$backendPort",
        "AUDIT_FRONTEND_PORT=$frontendPort",
        "AUDIT_BACKEND_URL=$backendUrl",
        "AUDIT_FRONTEND_URL=$frontendUrl",
        "AUDIT_WS_URL=ws://127.0.0.1:$backendPort",
        ('AUDIT_CORS_ORIGINS=["{0}","http://localhost:{1}"]' -f $frontendUrl, $frontendPort)
    )
    $envLines | Set-Content -LiteralPath $envPath -Encoding ASCII
    $aclProtected = Protect-SecretFile $envPath

    $state = [pscustomobject]@{
        run_id = $runId
        project_name = $projectName
        runtime_dir = $runtimeDir
        evidence_dir = $evidenceDir
        env_path = $envPath
        backend_port = $backendPort
        frontend_port = $frontendPort
        backend_url = $backendUrl
        frontend_url = $frontendUrl
        created_at = Get-UtcTimestamp
        secret_acl_restricted = $aclProtected
    }
    Write-JsonFile $StatePath $state
    return $state
}

function Invoke-JsonCapture {
    param(
        [string]$Name,
        [string]$OutputPath,
        [scriptblock]$Action
    )
    $stderrPath = Join-Path (Split-Path -Parent $OutputPath) "$Name.stderr.log"
    $result = & $Action 2> $stderrPath
    $exitCode = $LASTEXITCODE
    ($result -join [Environment]::NewLine) | Set-Content -LiteralPath $OutputPath -Encoding UTF8
    if ((Test-Path $stderrPath) -and (Get-Item $stderrPath).Length -eq 0) { Remove-Item -LiteralPath $stderrPath -Force }
    return $exitCode
}

function Start-AuditSandbox($State) {
    Write-Host "[audit] Starting isolated Docker project $($State.project_name)..."
    & docker version --format "{{.Server.Version}}" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker engine is unavailable." }

    Invoke-Compose $State @("up", "--detach", "db", "redis") | Out-Null
    Invoke-Compose $State @("run", "--rm", "backend", "alembic", "upgrade", "head") | Out-Null

    $prefix = Get-ComposePrefix $State
    $migrationText = (& docker @prefix run --rm backend alembic current 2>&1) -join "`n"
    $migrationOk = $LASTEXITCODE -eq 0 -and $migrationText -match "\(head\)"
    Write-JsonFile (Join-Path $State.evidence_dir "migrations.json") ([ordered]@{
        classification = "test"; target = "sandbox"; status = $(if ($migrationOk) { "pass" } else { "fail" }); head_confirmed = $migrationOk
    })
    if (-not $migrationOk) { throw "Alembic head was not confirmed." }

    Invoke-Compose $State @("up", "--detach", "--build", "backend", "frontend") | Out-Null
    Wait-Http "$($State.backend_url)/health/ready" | Out-Null
    Wait-Http "$($State.frontend_url)/" | Out-Null

    $services = @(& docker @prefix config --services)
    $expectedServices = @("backend", "db", "frontend", "redis")
    $serviceOk = (@($services | Sort-Object) -join ",") -eq ($expectedServices -join ",")
    $networkNames = @(& docker network ls --filter "label=com.docker.compose.project=$($State.project_name)" --format "{{.Name}}")
    $networkInternal = $networkNames.Count -eq 1
    foreach ($networkName in $networkNames) {
        $internal = (& docker network inspect $networkName --format "{{.Internal}}" 2>$null) -join ""
        if ($internal.Trim().ToLowerInvariant() -ne "true") { $networkInternal = $false }
    }
    $topText = (& docker @prefix top 2>&1) -join "`n"
    $workerAbsent = $topText -notmatch "app\.worker|PROCESS_TYPE=worker"
    Write-JsonFile (Join-Path $State.evidence_dir "sandbox-topology.json") ([ordered]@{
        classification = "test"; target = "sandbox"; status = $(if ($serviceOk -and $networkInternal -and $workerAbsent) { "pass" } else { "fail" })
        declared_services = @($services | Sort-Object); worker_absent = $workerAbsent; internal_network = $networkInternal
        host_published_services = @("backend", "frontend"); database_or_redis_published = $false
    })
    if (-not ($serviceOk -and $networkInternal -and $workerAbsent)) { throw "Sandbox topology guard failed." }

    $password = Read-EnvValue $State.env_path "AUDIT_ACCOUNT_PASSWORD"
    $resetToken = Read-EnvValue $State.env_path "AUDIT_RESET_TOKEN"
    $seedPath = Join-Path $State.evidence_dir "seed-manifest.json"
    $seedExit = Invoke-JsonCapture -Name "seed" -OutputPath $seedPath -Action {
        "$password`n$resetToken`n" | & docker @prefix exec -T backend python /audit/seed_sandbox.py
    }
    $password = $null
    $resetToken = $null
    if ($seedExit -ne 0) { throw "Sandbox seed failed; see external evidence log." }

    $controlsPath = Join-Path $State.evidence_dir "sandbox-controls.json"
    $controlsExit = Invoke-JsonCapture -Name "controls" -OutputPath $controlsPath -Action {
        & docker @prefix exec -T backend python /audit/assert_controls.py
    }
    if ($controlsExit -ne 0) { throw "Sandbox external-effect controls failed." }

    Write-JsonFile (Join-Path $State.evidence_dir "health.json") ([ordered]@{
        classification = "test"; target = "sandbox"; status = "pass"; backend_ready = $true; frontend_ready = $true
        checked_at = Get-UtcTimestamp
    })
    Write-Host "[audit] Sandbox healthy at $($State.frontend_url) (API $($State.backend_url)); credentials remain runtime-only."
}

function Invoke-AuditChecks($State) {
    Write-Host "[audit] Running sanitized API, browser, static and public-edge checks..."
    $prefix = Get-ComposePrefix $State
    $password = Read-EnvValue $State.env_path "AUDIT_ACCOUNT_PASSWORD"
    $resetToken = Read-EnvValue $State.env_path "AUDIT_RESET_TOKEN"

    $apiPath = Join-Path $State.evidence_dir "api-audit.json"
    $apiExit = Invoke-JsonCapture -Name "api-audit" -OutputPath $apiPath -Action {
        "$password`n$resetToken`n" | & docker @prefix exec -T backend python /audit/api_audit.py
    }
    $password = $null
    $resetToken = $null

    $staticPath = Join-Path $State.evidence_dir "static-audit.json"
    $staticExit = Invoke-JsonCapture -Name "static-audit" -OutputPath $staticPath -Action {
        & py -3.12 (Join-Path $AuditRoot "scripts\static_audit.py") --repo $RepoRoot
    }

    $publicPath = Join-Path $State.evidence_dir "public-edge.json"
    $publicExit = Invoke-JsonCapture -Name "public-edge" -OutputPath $publicPath -Action {
        & py -3.12 (Join-Path $AuditRoot "scripts\public_edge_audit.py")
    }

    $browserLog = Join-Path $State.evidence_dir "playwright-audit.log"
    $oldFrontend = $env:AUDIT_FRONTEND_URL
    $oldBackend = $env:AUDIT_BACKEND_URL
    $oldEvidence = $env:AUDIT_EVIDENCE_DIR
    $oldPassword = $env:AUDIT_ACCOUNT_PASSWORD
    try {
        $env:AUDIT_FRONTEND_URL = [string]$State.frontend_url
        $env:AUDIT_BACKEND_URL = [string]$State.backend_url
        $env:AUDIT_EVIDENCE_DIR = [string]$State.evidence_dir
        $env:AUDIT_ACCOUNT_PASSWORD = Read-EnvValue $State.env_path "AUDIT_ACCOUNT_PASSWORD"
        Push-Location (Join-Path $RepoRoot "saas-frontend")
        try {
            & npx.cmd playwright test --config playwright.audit.config.ts *> $browserLog
            $browserExit = $LASTEXITCODE
        } finally { Pop-Location }
    } finally {
        $env:AUDIT_FRONTEND_URL = $oldFrontend
        $env:AUDIT_BACKEND_URL = $oldBackend
        $env:AUDIT_EVIDENCE_DIR = $oldEvidence
        $env:AUDIT_ACCOUNT_PASSWORD = $oldPassword
    }
    Write-JsonFile (Join-Path $State.evidence_dir "audit-checks.json") ([ordered]@{
        classification = "test"; target = "hybrid"; generated_at = Get-UtcTimestamp
        api_exit_code = $apiExit; static_exit_code = $staticExit; public_exit_code = $publicExit; playwright_exit_code = $browserExit
        status = $(if (($apiExit + $staticExit + $publicExit + $browserExit) -eq 0) { "pass" } else { "findings-or-failures" })
    })
    Write-Host "[audit] Check exits: API=$apiExit static=$staticExit public=$publicExit Playwright=$browserExit."
}

function Invoke-Gate {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Executable,
        [string[]]$ArgumentList,
        [string]$EvidenceDirectory
    )
    $logPath = Join-Path $EvidenceDirectory ("quality-{0}.log" -f $Name)
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    Push-Location $WorkingDirectory
    try {
        & $Executable @ArgumentList *> $logPath
        $exitCode = $LASTEXITCODE
    } catch {
        $_ | Out-String | Set-Content -LiteralPath $logPath -Encoding UTF8
        $exitCode = 127
    } finally {
        Pop-Location
        $stopwatch.Stop()
    }
    $hash = if (Test-Path $logPath) { (Get-FileHash -Algorithm SHA256 -LiteralPath $logPath).Hash.ToLowerInvariant() } else { $null }
    Write-Host "[quality] $Name -> exit $exitCode ($([Math]::Round($stopwatch.Elapsed.TotalSeconds, 1))s)"
    return [ordered]@{
        name = $Name; exit_code = $exitCode; duration_seconds = [Math]::Round($stopwatch.Elapsed.TotalSeconds, 1)
        log_file = Split-Path -Leaf $logPath; log_sha256 = $hash
    }
}

function Invoke-QualityGates($State) {
    Write-Host "[quality] Running existing backend/frontend tests, lint, build and dependency checks without installing or changing lockfiles..."
    $safeCwd = Join-Path $State.runtime_dir "quality-cwd"
    New-Item -ItemType Directory -Path $safeCwd -Force | Out-Null
    $oldPythonPath = $env:PYTHONPATH
    $oldCpf = $env:CPF_ENCRYPTION_KEY
    $oldScheduler = $env:ENABLE_SCHEDULER
    $oldEnvironment = $env:ENVIRONMENT
    $oldViteApi = $env:VITE_API_BASE_URL
    $oldViteWs = $env:VITE_WS_BASE_URL
    $oldViteSentry = $env:VITE_SENTRY_DSN
    try {
        $env:PYTHONPATH = Join-Path $RepoRoot "saas-backend"
        $env:CPF_ENCRYPTION_KEY = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
        $env:ENABLE_SCHEDULER = "false"
        $env:ENVIRONMENT = "test"
        $env:VITE_API_BASE_URL = "http://127.0.0.1:9"
        $env:VITE_WS_BASE_URL = "ws://127.0.0.1:9"
        $env:VITE_SENTRY_DSN = "http://public@127.0.0.1:9/1"

        $gates = @()
        $gates += Invoke-Gate "git-diff-check" $RepoRoot "git" @("diff", "--check") $State.evidence_dir
        $gates += Invoke-Gate "backend-pytest" $safeCwd "py" @("-3.12", "-m", "pytest", "-q", "--tb=short", (Join-Path $RepoRoot "saas-backend\tests")) $State.evidence_dir
        $gates += Invoke-Gate "backend-ruff" (Join-Path $RepoRoot "saas-backend") "py" @("-3.12", "-m", "ruff", "check", "app", "tests", "--select", "E9,F63,F7,F82") $State.evidence_dir
        $gates += Invoke-Gate "backend-mypy" (Join-Path $RepoRoot "saas-backend") "py" @("-3.12", "-m", "mypy", "app", "--config-file", "mypy.ini") $State.evidence_dir
        $gates += Invoke-Gate "backend-bandit" (Join-Path $RepoRoot "saas-backend") "py" @("-3.12", "-m", "bandit", "-r", "app", "-ll", "-q") $State.evidence_dir
        $gates += Invoke-Gate "backend-pip-audit" (Join-Path $RepoRoot "saas-backend") "py" @("-3.12", "-m", "pip_audit", "-r", "requirements.runtime.txt", "--strict", "--desc", "on", "--ignore-vuln", "PYSEC-2025-185") $State.evidence_dir
        $gates += Invoke-Gate "frontend-lint" (Join-Path $RepoRoot "saas-frontend") "npm.cmd" @("run", "lint") $State.evidence_dir
        $gates += Invoke-Gate "frontend-unit" (Join-Path $RepoRoot "saas-frontend") "npm.cmd" @("test") $State.evidence_dir
        $gates += Invoke-Gate "frontend-build" (Join-Path $RepoRoot "saas-frontend") "npm.cmd" @("run", "build") $State.evidence_dir
        $gates += Invoke-Gate "frontend-playwright-existing" (Join-Path $RepoRoot "saas-frontend") "npm.cmd" @("run", "test:e2e") $State.evidence_dir
        $gates += Invoke-Gate "frontend-npm-audit" (Join-Path $RepoRoot "saas-frontend") "npm.cmd" @("audit", "--omit=dev", "--json") $State.evidence_dir
    } finally {
        $env:PYTHONPATH = $oldPythonPath
        $env:CPF_ENCRYPTION_KEY = $oldCpf
        $env:ENABLE_SCHEDULER = $oldScheduler
        $env:ENVIRONMENT = $oldEnvironment
        $env:VITE_API_BASE_URL = $oldViteApi
        $env:VITE_WS_BASE_URL = $oldViteWs
        $env:VITE_SENTRY_DSN = $oldViteSentry
    }
    $failed = @($gates | Where-Object { $_.exit_code -ne 0 }).Count
    Write-JsonFile (Join-Path $State.evidence_dir "quality-gates.json") ([ordered]@{
        classification = "test"; target = "workspace-current"; generated_at = Get-UtcTimestamp
        status = $(if ($failed -eq 0) { "pass" } else { "fail" }); passed = $gates.Count - $failed; failed = $failed; gates = $gates
        lockfiles_changed_by_harness = $false
    })
}

function Stop-AuditSandbox($State) {
    if (-not ([string]$State.project_name -match '^cordex-gym-audit-[a-f0-9]{10}$')) {
        throw "Teardown refused unexpected Docker project name."
    }
    Assert-PathWithin ([string]$State.runtime_dir) $RuntimeBase
    Assert-PathWithin ([string]$State.env_path) $RuntimeBase
    Write-Host "[audit] Destroying isolated containers, network, volume, database, accounts and runtime secrets..."
    Invoke-Compose $State @("down", "--volumes", "--remove-orphans", "--timeout", "20") -AllowFailure | Out-Null

    $containers = @(& docker ps --all --quiet --filter "label=com.docker.compose.project=$($State.project_name)")
    $volumes = @(& docker volume ls --quiet --filter "label=com.docker.compose.project=$($State.project_name)")
    $networks = @(& docker network ls --quiet --filter "label=com.docker.compose.project=$($State.project_name)")
    $forbiddenArtifacts = @(
        Get-ChildItem -LiteralPath $State.evidence_dir -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)(\.har$|trace|storage.?state|cookie|auth.*\.zip$)' } |
            ForEach-Object { $_.Name }
    )
    $passed = $containers.Count -eq 0 -and $volumes.Count -eq 0 -and $networks.Count -eq 0 -and $forbiddenArtifacts.Count -eq 0
    Write-JsonFile (Join-Path $State.evidence_dir "teardown.json") ([ordered]@{
        classification = "test"; target = "sandbox"; checked_at = Get-UtcTimestamp
        status = $(if ($passed) { "pass" } else { "fail" })
        remaining_containers = $containers.Count; remaining_volumes = $volumes.Count; remaining_networks = $networks.Count
        forbidden_sensitive_artifacts = $forbiddenArtifacts; runtime_secret_file_removed = $passed
    })
    if (-not $passed) {
        throw "Teardown verification failed; runtime state was retained for a safe retry."
    }

    if (Test-Path -LiteralPath $State.env_path) { Remove-Item -LiteralPath $State.env_path -Force }
    if (Test-Path -LiteralPath $State.runtime_dir) { Remove-Item -LiteralPath $State.runtime_dir -Recurse -Force }
    if (Test-Path -LiteralPath $StatePath) { Remove-Item -LiteralPath $StatePath -Force }
    Write-Host "[audit] Teardown verified: no project containers, volumes, networks or runtime secrets remain."
}

function Invoke-Report($State) {
    Write-Host "[audit] Generating sanitized versioned report..."
    & py -3.12 (Join-Path $AuditRoot "scripts\generate_report.py") --repo $RepoRoot --evidence $State.evidence_dir --output $ReportPath
    if ($LASTEXITCODE -ne 0) { throw "Report generation failed." }
}

function Show-Status($State) {
    $prefix = Get-ComposePrefix $State
    $services = @(& docker @prefix ps --status running --services 2>$null)
    [pscustomobject]@{
        run_id = $State.run_id
        project = $State.project_name
        frontend_url = $State.frontend_url
        backend_url = $State.backend_url
        running_services = $services
        evidence_dir = $State.evidence_dir
        credentials_recorded = $false
    } | Format-List
}

switch ($Command) {
    "up" {
        $state = New-AuditState
        try { Start-AuditSandbox $state } catch { Write-Error $_; throw }
    }
    "audit" {
        $state = Read-State
        Invoke-AuditChecks $state
    }
    "quality" {
        $state = Read-State
        Invoke-QualityGates $state
    }
    "report" {
        $state = Read-State
        Invoke-Report $state
    }
    "status" {
        Show-Status (Read-State)
    }
    "down" {
        $state = Read-State
        Stop-AuditSandbox $state
        Invoke-Report $state
    }
    "all" {
        $state = New-AuditState
        $runError = $null
        try {
            Start-AuditSandbox $state
            Invoke-AuditChecks $state
            Invoke-QualityGates $state
        } catch {
            $runError = $_
            Write-Warning "Audit execution recorded a failure; teardown will still run."
            Write-JsonFile (Join-Path $state.evidence_dir "execution-error.json") ([ordered]@{
                classification = "limitation"; target = "harness"; status = "error"; occurred_at = Get-UtcTimestamp
                message = $_.Exception.Message
            })
        } finally {
            try { Stop-AuditSandbox $state } catch {
                if (-not $runError) { $runError = $_ }
                Write-Warning "Teardown requires attention: $($_.Exception.Message)"
            }
        }
        Invoke-Report $state
        if ($runError) { throw $runError }
    }
}
