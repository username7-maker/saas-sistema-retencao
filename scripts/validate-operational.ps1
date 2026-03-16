Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:EnvFileName = ".env.staging.local"
$script:EnvFilePath = Join-Path $script:RepoRoot $script:EnvFileName
$script:ComposeFileName = "docker-compose.yml"
$script:FrontendDir = Join-Path $script:RepoRoot "saas-frontend"
$script:ArtifactsRoot = Join-Path $script:RepoRoot "artifacts\operational-validation"
$script:RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$script:RunDir = Join-Path $script:ArtifactsRoot $script:RunId
$script:StateFile = Join-Path ([System.IO.Path]::GetTempPath()) "ai-gym-os-operational-validation-state.json"
$script:ServicesStarted = $false
$script:Summary = [ordered]@{
    run_id = $script:RunId
    env_file = $script:EnvFileName
    artifacts_dir = $script:RunDir
    checks = [ordered]@{}
    scheduler = [ordered]@{}
    auth = [ordered]@{}
    browser = $null
}


function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}


function Write-Info {
    param([string]$Message)
    Write-Host "    $Message"
}


function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}


function Save-Artifact {
    param(
        [string]$Name,
        [string]$Content
    )

    $path = Join-Path $script:RunDir $Name
    $directory = Split-Path -Parent $path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Force $directory | Out-Null
    }
    Set-Content -Path $path -Value $Content -Encoding UTF8
    return $path
}


function Invoke-External {
    param(
        [string]$Command,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $script:RepoRoot,
        [switch]$AllowFailure
    )

    Push-Location $WorkingDirectory
    try {
        $rawOutput = & $Command @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $outputText = ""
    if ($null -ne $rawOutput) {
        $outputText = ($rawOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    }

    if (-not $AllowFailure -and $exitCode -ne 0) {
        throw "Command failed ($Command $($Arguments -join ' ')).`n$outputText"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = $outputText.Trim()
    }
}


function Invoke-Compose {
    param(
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    $composeArgs = @("compose", "--env-file", $script:EnvFileName, "-f", $script:ComposeFileName) + $Arguments
    return Invoke-External -Command "docker" -Arguments $composeArgs -WorkingDirectory $script:RepoRoot -AllowFailure:$AllowFailure
}


function Parse-EnvFile {
    param([string]$Path)

    $values = @{}
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }
        $key = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1)
        $values[$key] = $value
    }
    return $values
}


function Get-ComposeContainerId {
    param([string]$Service)

    $result = Invoke-Compose -Arguments @("ps", "-q", $Service)
    $id = $result.Output.Trim()
    if (-not $id) {
        throw "Could not resolve container id for service '$Service'."
    }
    return $id
}


function Get-ContainerState {
    param([string]$Service)

    $containerId = Get-ComposeContainerId -Service $Service
    $state = Invoke-External -Command "docker" -Arguments @("inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", $containerId)
    return $state.Output.Trim()
}


function Wait-ContainerState {
    param(
        [string]$Service,
        [string[]]$ExpectedStates,
        [int]$TimeoutSeconds = 300,
        [int]$SleepSeconds = 5
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $state = Get-ContainerState -Service $Service
            if ($ExpectedStates -contains $state) {
                Write-Info "$Service state: $state"
                return $state
            }
            Write-Info "Waiting for $Service. Current state: $state"
        }
        catch {
            Write-Info "Waiting for $Service container to appear..."
        }
        Start-Sleep -Seconds $SleepSeconds
    }
    while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for service '$Service' to reach state(s): $($ExpectedStates -join ', ')."
}


function Invoke-HttpRequest {
    param(
        [ValidateSet("GET", "POST", "OPTIONS", "DELETE")]
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [int]$TimeoutSeconds = 30
    )

    $params = @{
        Method      = $Method
        Uri         = $Url
        Headers     = $Headers
        TimeoutSec  = $TimeoutSeconds
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }
    return Invoke-WebRequest @params
}


function Invoke-JsonRequest {
    param(
        [ValidateSet("GET", "POST", "DELETE")]
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [int]$TimeoutSeconds = 30
    )

    $params = @{
        Method      = $Method
        Uri         = $Url
        Headers     = $Headers
        TimeoutSec  = $TimeoutSeconds
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }
    return Invoke-RestMethod @params
}


function Wait-Http {
    param(
        [string]$Url,
        [scriptblock]$Validator,
        [int]$TimeoutSeconds = 300,
        [int]$SleepSeconds = 5
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = $null
    do {
        try {
            $response = Invoke-HttpRequest -Method "GET" -Url $Url -TimeoutSeconds 15
            if (& $Validator $response) {
                return $response
            }
            $lastError = "Validator rejected response."
        }
        catch {
            $lastError = $_.Exception.Message
        }
        Write-Info "Waiting for HTTP endpoint $Url"
        Start-Sleep -Seconds $SleepSeconds
    }
    while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for '$Url'. Last error: $lastError"
}


function Save-ServiceLogs {
    param([string[]]$Services)

    foreach ($service in $Services) {
        $logs = Invoke-Compose -Arguments @("logs", "--tail", "200", $service) -AllowFailure
        Save-Artifact -Name "logs\$service.log" -Content $logs.Output | Out-Null
    }
    $combined = Invoke-Compose -Arguments @("logs", "--tail", "200", "backend", "worker", "frontend") -AllowFailure
    Save-Artifact -Name "logs\combined.log" -Content $combined.Output | Out-Null
}


function Login-ValidationUser {
    param(
        [string]$ApiBaseUrl,
        [hashtable]$Identity
    )

    return Invoke-JsonRequest -Method "POST" -Url "$ApiBaseUrl/api/v1/auth/login" -Body @{
        email = $Identity.email
        password = $Identity.password
        gym_slug = $Identity.gym_slug
    }
}


function Get-ValidationIdentity {
    param([string]$ApiBaseUrl)

    if (Test-Path $script:StateFile) {
        try {
            $stored = Get-Content $script:StateFile -Raw | ConvertFrom-Json
            $existing = @{
                full_name = [string]$stored.full_name
                email = [string]$stored.email
                password = [string]$stored.password
                gym_name = [string]$stored.gym_name
                gym_slug = [string]$stored.gym_slug
            }
            $tokens = Login-ValidationUser -ApiBaseUrl $ApiBaseUrl -Identity $existing
            return [pscustomobject]@{
                Identity = $existing
                Tokens = $tokens
                Source = "state-file"
            }
        }
        catch {
            Write-Info "Cached validation identity could not log in. Creating a new one."
        }
    }

    $suffix = Get-Date -Format "yyyyMMddHHmmss"
    $identity = @{
        full_name = "Operational Validation Owner"
        email = "ops-$suffix@example.com"
        password = "OperationalPass123!"
        gym_name = "AI GYM OS Validation $suffix"
        gym_slug = "ops-$suffix"
    }

    try {
        Invoke-JsonRequest -Method "POST" -Url "$ApiBaseUrl/api/v1/auth/register" -Body $identity | Out-Null
    }
    catch {
        throw "Could not create a validation user through /api/v1/auth/register. $_"
    }

    $tokens = Login-ValidationUser -ApiBaseUrl $ApiBaseUrl -Identity $identity
    ($identity | ConvertTo-Json -Depth 3) | Set-Content -Path $script:StateFile -Encoding UTF8

    return [pscustomobject]@{
        Identity = $identity
        Tokens = $tokens
        Source = "register"
    }
}


function Get-HeaderValueText {
    param(
        [object]$Headers,
        [string]$Name
    )

    if ($null -eq $Headers) {
        return ""
    }

    foreach ($key in $Headers.Keys) {
        if ($key.ToString().Equals($Name, [System.StringComparison]::OrdinalIgnoreCase)) {
            $value = $Headers[$key]
            if ($value -is [System.Array]) {
                return ($value -join ", ")
            }
            return $value.ToString()
        }
    }

    return ""
}


function Test-HeaderValue {
    param(
        [object]$Headers,
        [string]$Name,
        [string]$ExpectedSubstring
    )

    $value = Get-HeaderValueText -Headers $Headers -Name $Name
    if (-not $value) {
        return $false
    }
    return $value.IndexOf($ExpectedSubstring, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
}


function Remove-ValidationMembers {
    param(
        [string]$ApiBaseUrl,
        [hashtable]$Headers,
        [string[]]$Names
    )

    foreach ($name in $Names) {
        $searchTerm = [System.Uri]::EscapeDataString($name)
        $membersResponse = Invoke-JsonRequest -Method "GET" -Url "$ApiBaseUrl/api/v1/members/?page=1&page_size=100&search=$searchTerm" -Headers $Headers
        $matches = @($membersResponse.items | Where-Object { $_.full_name -eq $name })
        foreach ($member in $matches) {
            Write-Info "Removing leftover validation member '$($member.full_name)' ($($member.id))"
            Invoke-JsonRequest -Method "DELETE" -Url "$ApiBaseUrl/api/v1/members/$($member.id)" -Headers $Headers | Out-Null
        }
    }
}


function Export-BrowserScript {
    $content = @'
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const outputDir = process.env.OPS_OUTPUT_DIR;
const frontendUrl = process.env.OPS_FRONTEND_URL;
const apiBaseUrl = process.env.OPS_API_BASE_URL;
const gymSlug = process.env.OPS_GYM_SLUG;
const email = process.env.OPS_EMAIL;
const password = process.env.OPS_PASSWORD;
const memberName = process.env.OPS_MEMBER_NAME;
const updatedMemberName = process.env.OPS_UPDATED_MEMBER_NAME;

function fail(message) {
  throw new Error(message);
}

const result = {
  dashboard_url: "",
  member_name: memberName,
  updated_member_name: updatedMemberName,
  api_requests: [],
  api_failures: [],
  cors_console_issues: [],
  cors_fetch: null,
  trace_file: "browser-trace.zip",
};

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true });
await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
const page = await context.newPage();

page.on("response", async (response) => {
  if (response.url().startsWith(apiBaseUrl)) {
    result.api_requests.push({
      url: response.url(),
      method: response.request().method(),
      status: response.status(),
    });
    if (response.status() >= 400) {
      result.api_failures.push({
        url: response.url(),
        method: response.request().method(),
        status: response.status(),
      });
    }
  }
});

page.on("console", (message) => {
  const text = message.text();
  if (/cors|cross-origin|access-control/i.test(text)) {
    result.cors_console_issues.push({
      type: message.type(),
      text,
    });
  }
});

page.on("requestfailed", (request) => {
  if (request.url().startsWith(apiBaseUrl)) {
    result.api_failures.push({
      url: request.url(),
      method: request.method(),
      status: "requestfailed",
      error: request.failure()?.errorText ?? "unknown",
    });
  }
});

try {
  await page.goto(`${frontendUrl}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.getByPlaceholder("academia-centro").fill(gymSlug);
  await page.getByPlaceholder("gestor@academia.com").fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("**/dashboard/executive", { timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 60000 });
  result.dashboard_url = page.url();

  const sectionHeading = page.getByRole("heading", { name: "Executivo" });
  await sectionHeading.waitFor({ state: "visible", timeout: 30000 });

  await page.goto(`${frontendUrl}/members`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 60000 });

  const addButton = page.getByRole("button", { name: /Adicionar Membro/ });
  await addButton.waitFor({ state: "visible", timeout: 30000 });
  await addButton.click();

  const addDrawer = page.locator("aside").filter({ hasText: "Adicionar Membro" });
  await addDrawer.locator('input[placeholder="Nome do membro"]').fill(memberName);
  await addDrawer.locator('input[placeholder="email@academia.com"]').fill("member+" + Date.now() + "@example.com");
  await addDrawer.locator('input[placeholder="(11) 99999-9999"]').fill("11999999999");
  await addDrawer.locator('input[type="number"]').fill("149.90");
  await addDrawer.locator('select').nth(0).selectOption("Mensal");
  await addDrawer.locator('select').nth(1).selectOption("evening");
  await addDrawer.getByRole("button", { name: "Criar membro" }).click();

  const createdRow = page.locator("tr", { hasText: memberName });
  await createdRow.waitFor({ state: "visible", timeout: 30000 });

  await createdRow.locator('button[title="Editar"]').click();

  const editDrawer = page.locator("aside").filter({ hasText: "Editar Membro" });
  await editDrawer.locator('input[placeholder="Nome do membro"]').fill(updatedMemberName);
  await editDrawer.locator('input[placeholder="Ex: Mensal, Trimestral"]').fill("Semestral");
  await editDrawer.locator('input[type="number"]').fill("199.90");
  await editDrawer.getByRole("button", { name: "Salvar" }).click();

  const updatedRow = page.locator("tr", { hasText: updatedMemberName });
  await updatedRow.waitFor({ state: "visible", timeout: 30000 });

  result.cors_fetch = await page.evaluate(async ({ url }) => {
    const token = localStorage.getItem("ai_gym_access_token");
    try {
      const response = await fetch(url, {
        method: "GET",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const text = await response.text();
      return {
        ok: response.ok,
        status: response.status,
        body_preview: text.slice(0, 160),
      };
    } catch (error) {
      return {
        ok: false,
        error: String(error),
      };
    }
  }, { url: `${apiBaseUrl}/api/v1/users/me` });

  if (!result.cors_fetch || result.cors_fetch.status !== 200) {
    fail(`Browser CORS fetch did not return 200: ${JSON.stringify(result.cors_fetch)}`);
  }

  if (result.api_failures.length > 0) {
    fail(`API request failures were detected: ${JSON.stringify(result.api_failures)}`);
  }

  if (!result.api_requests.some((item) => item.url.startsWith(`${apiBaseUrl}/api/v1/`))) {
    fail("The frontend did not issue requests to the expected API base URL.");
  }

  if (result.cors_console_issues.length > 0) {
    fail(`Browser reported CORS console issues: ${JSON.stringify(result.cors_console_issues)}`);
  }

  await page.screenshot({ path: path.join(outputDir, "browser-success.png"), fullPage: true });
  fs.writeFileSync(path.join(outputDir, "browser-results.json"), JSON.stringify(result, null, 2));
} catch (error) {
  try {
    await page.screenshot({ path: path.join(outputDir, "browser-failure.png"), fullPage: true });
  } catch {}
  result.error = String(error);
  fs.writeFileSync(path.join(outputDir, "browser-results.json"), JSON.stringify(result, null, 2));
  console.error(String(error));
  process.exitCode = 1;
} finally {
  try {
    await context.tracing.stop({ path: path.join(outputDir, "browser-trace.zip") });
  } catch {}
  await context.close();
  await browser.close();
}
'@

    $path = Join-Path $script:RunDir "browser\operational-check.mjs"
    $directory = Split-Path -Parent $path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Force $directory | Out-Null
    }
    Set-Content -Path $path -Value $content -Encoding UTF8
    return $path
}


function Read-BrowserResult {
    $browserResultPath = Join-Path $script:RunDir "browser\browser-results.json"
    if (-not (Test-Path $browserResultPath)) {
        throw "Browser validation result file was not created."
    }
    return Get-Content $browserResultPath -Raw | ConvertFrom-Json
}


function Save-PartialDiagnostics {
    if (-not $script:ServicesStarted) {
        return
    }

    try {
        Save-ServiceLogs -Services @("backend", "worker", "frontend")
        $psOutput = Invoke-Compose -Arguments @("ps") -AllowFailure
        Save-Artifact -Name "compose-ps.txt" -Content $psOutput.Output | Out-Null
    }
    catch {
        Write-Info "Could not save partial diagnostics: $($_.Exception.Message)"
    }
}


try {
    if (-not (Test-Path $script:RunDir)) {
        New-Item -ItemType Directory -Force $script:RunDir | Out-Null
    }

    Write-Step "Validating prerequisites"
    Ensure-Command -Name "docker"
    Ensure-Command -Name "node"
    Ensure-Command -Name "npm"
    if (-not (Test-Path $script:EnvFilePath)) {
        throw "Expected env file '$($script:EnvFileName)' was not found at repo root."
    }
    if (-not (Test-Path (Join-Path $script:FrontendDir "node_modules\playwright"))) {
        throw "Frontend Playwright dependency is missing. Run 'npm ci' in saas-frontend before this script."
    }
    $envValues = Parse-EnvFile -Path $script:EnvFilePath
    foreach ($requiredKey in @("FRONTEND_URL", "VITE_API_BASE_URL", "CORS_ORIGINS")) {
        if (-not $envValues.ContainsKey($requiredKey) -or -not $envValues[$requiredKey]) {
            throw "Required key '$requiredKey' was not found in $($script:EnvFileName)."
        }
    }
    $frontendUrl = $envValues["FRONTEND_URL"].TrimEnd("/")
    $apiBaseUrl = $envValues["VITE_API_BASE_URL"].TrimEnd("/")
    $script:Summary.checks.prerequisites = $true
    Save-Artifact -Name "env-used.txt" -Content ((Get-Content $script:EnvFilePath) -join [Environment]::NewLine) | Out-Null

    Write-Step "Rendering docker compose config"
    $composeConfig = Invoke-Compose -Arguments @("config")
    Save-Artifact -Name "compose-config.yaml" -Content $composeConfig.Output | Out-Null
    $script:Summary.checks.compose_config = $true

    Write-Step "Starting the stack"
    $composeUp = Invoke-Compose -Arguments @("up", "--build", "-d")
    Save-Artifact -Name "compose-up.txt" -Content $composeUp.Output | Out-Null
    $script:ServicesStarted = $true
    $script:Summary.checks.compose_up = $true

    Write-Step "Waiting for db, backend, worker and frontend containers"
    Wait-ContainerState -Service "db" -ExpectedStates @("healthy")
    Wait-ContainerState -Service "backend" -ExpectedStates @("healthy")
    Wait-ContainerState -Service "worker" -ExpectedStates @("running")
    Wait-ContainerState -Service "frontend" -ExpectedStates @("running")
    $composePs = Invoke-Compose -Arguments @("ps")
    Save-Artifact -Name "compose-ps.txt" -Content $composePs.Output | Out-Null
    $script:Summary.checks.compose_ps = $true

    Write-Step "Applying migrations inside backend"
    $alembicUpgrade = Invoke-Compose -Arguments @("exec", "-T", "backend", "alembic", "upgrade", "head")
    Save-Artifact -Name "alembic-upgrade.txt" -Content $alembicUpgrade.Output | Out-Null
    $alembicCurrent = Invoke-Compose -Arguments @("exec", "-T", "backend", "alembic", "current")
    Save-Artifact -Name "alembic-current.txt" -Content $alembicCurrent.Output | Out-Null
    if ($alembicCurrent.Output -notmatch "\(head\)") {
        throw "alembic current did not report head. Output: $($alembicCurrent.Output)"
    }
    $script:Summary.checks.alembic_upgrade = $true

    Write-Step "Checking frontend HTTP response"
    $frontendResponse = Wait-Http -Url $frontendUrl -Validator {
        param($response)
        return $response.StatusCode -eq 200 -and $response.Content -match 'id="root"'
    }
    Save-Artifact -Name "frontend-root.html" -Content $frontendResponse.Content | Out-Null
    $script:Summary.checks.frontend_http = $true

    Write-Step "Checking API health endpoints"
    $healthResponse = Wait-Http -Url "$apiBaseUrl/health" -Validator {
        param($response)
        return $response.StatusCode -eq 200 -and $response.Content -match '"status"\s*:\s*"ok"'
    }
    Save-Artifact -Name "api-health.json" -Content $healthResponse.Content | Out-Null

    $readyResponse = Wait-Http -Url "$apiBaseUrl/health/ready" -Validator {
        param($response)
        return $response.StatusCode -eq 200 -and $response.Content -match '"status"\s*:\s*"ok"'
    }
    Save-Artifact -Name "api-ready.json" -Content $readyResponse.Content | Out-Null
    $script:Summary.checks.api_health = $true
    $script:Summary.checks.api_ready = $true

    Write-Step "Collecting service logs"
    Save-ServiceLogs -Services @("backend", "worker", "frontend")
    $script:Summary.checks.logs_collected = $true

    Write-Step "Checking scheduler isolation"
    $backendScheduler = Invoke-Compose -Arguments @("exec", "-T", "backend", "python", "-c", "from app.core.config import settings; print(str(settings.enable_scheduler).lower())")
    $workerScheduler = Invoke-Compose -Arguments @("exec", "-T", "worker", "python", "-c", "from app.core.config import settings; print(str(settings.enable_scheduler).lower())")
    $backendContainerId = Get-ComposeContainerId -Service "backend"
    $workerContainerId = Get-ComposeContainerId -Service "worker"
    $backendCommand = Invoke-External -Command "docker" -Arguments @("inspect", "--format", "{{json .Config.Cmd}}", $backendContainerId)
    $workerCommand = Invoke-External -Command "docker" -Arguments @("inspect", "--format", "{{json .Config.Cmd}}", $workerContainerId)

    $backendLogText = Get-Content (Join-Path $script:RunDir "logs\backend.log") -Raw
    $workerLogText = Get-Content (Join-Path $script:RunDir "logs\worker.log") -Raw
    $backendDisabledMarker = "Scheduler disabled in API process; dedicated worker must run scheduled jobs."
    $backendEnabledMarker = "Scheduler enabled in API process; starting scheduler in API lifespan."
    $workerStartedMarker = "Scheduler worker started dedicated scheduler process."

    $script:Summary.scheduler = [ordered]@{
        backend_enable_scheduler = $backendScheduler.Output.Trim()
        worker_enable_scheduler = $workerScheduler.Output.Trim()
        backend_command = $backendCommand.Output.Trim()
        worker_command = $workerCommand.Output.Trim()
        backend_log_has_disabled_marker = [bool]($backendLogText -match [regex]::Escape($backendDisabledMarker))
        backend_log_has_enabled_marker = [bool]($backendLogText -match [regex]::Escape($backendEnabledMarker))
        worker_log_has_started_marker = [bool]($workerLogText -match [regex]::Escape($workerStartedMarker))
    }

    if ($backendScheduler.Output.Trim() -ne "false") {
        throw "backend ENABLE_SCHEDULER check failed. Expected false."
    }
    if ($workerScheduler.Output.Trim() -ne "true") {
        throw "worker scheduler check failed. Expected true."
    }
    if ($backendCommand.Output -notmatch "uvicorn") {
        throw "backend container command does not look like the API process."
    }
    if ($workerCommand.Output -notmatch "app\.worker") {
        throw "worker container command does not look like app.worker."
    }
    if ($backendLogText -notmatch [regex]::Escape($backendDisabledMarker)) {
        throw "backend logs do not contain the expected scheduler-disabled marker."
    }
    if ($backendLogText -match [regex]::Escape($backendEnabledMarker)) {
        throw "backend logs show scheduler startup even though the API should run with ENABLE_SCHEDULER=false."
    }
    if ($workerLogText -notmatch [regex]::Escape($workerStartedMarker)) {
        throw "worker logs do not contain the expected dedicated scheduler startup marker."
    }
    $script:Summary.checks.scheduler_isolated = $true

    Write-Step "Preparing validation user and API session"
    $authContext = Get-ValidationIdentity -ApiBaseUrl $apiBaseUrl
    $authHeaders = @{
        Authorization = "Bearer $($authContext.Tokens.access_token)"
    }
    $meResponse = Invoke-JsonRequest -Method "GET" -Url "$apiBaseUrl/api/v1/users/me" -Headers $authHeaders
    Save-Artifact -Name "auth-me.json" -Content ($meResponse | ConvertTo-Json -Depth 10) | Out-Null
    $script:Summary.auth = [ordered]@{
        source = $authContext.Source
        email = $authContext.Identity.email
        gym_slug = $authContext.Identity.gym_slug
        me_email = $meResponse.email
    }
    $script:Summary.checks.auth_login = $true

    Write-Step "Validating CORS preflight"
    $preflight = Invoke-HttpRequest -Method "OPTIONS" -Url "$apiBaseUrl/api/v1/users/me" -Headers @{
        Origin = $frontendUrl
        "Access-Control-Request-Method" = "GET"
        "Access-Control-Request-Headers" = "Authorization, Content-Type"
    } -TimeoutSeconds 15
    Save-Artifact -Name "cors-preflight.txt" -Content ($preflight.Headers | Out-String) | Out-Null
    if ($preflight.StatusCode -ne 200) {
        throw "CORS preflight did not return HTTP 200. Status: $($preflight.StatusCode)"
    }
    if (-not (Test-HeaderValue -Headers $preflight.Headers -Name "Access-Control-Allow-Origin" -ExpectedSubstring $frontendUrl)) {
        throw "CORS preflight did not expose the expected Access-Control-Allow-Origin header."
    }
    if (-not (Test-HeaderValue -Headers $preflight.Headers -Name "Access-Control-Allow-Headers" -ExpectedSubstring "Authorization")) {
        throw "CORS preflight did not allow the Authorization header."
    }
    if (-not (Test-HeaderValue -Headers $preflight.Headers -Name "Access-Control-Allow-Methods" -ExpectedSubstring "GET")) {
        throw "CORS preflight did not allow the GET method."
    }
    if (-not (Test-HeaderValue -Headers $preflight.Headers -Name "Access-Control-Allow-Credentials" -ExpectedSubstring "true")) {
        throw "CORS preflight did not allow credentials."
    }
    $script:Summary.checks.cors_preflight = $true

    Write-Step "Running browser validation for login, dashboard, members and browser-side CORS"
    $browserScript = Export-BrowserScript
    $memberName = "Operational Validation Member [$($authContext.Identity.gym_slug)]"
    $updatedMemberName = "$memberName Updated"
    Remove-ValidationMembers -ApiBaseUrl $apiBaseUrl -Headers $authHeaders -Names @($memberName, $updatedMemberName)

    $browserEnv = @{
        OPS_OUTPUT_DIR = (Join-Path $script:RunDir "browser")
        OPS_FRONTEND_URL = $frontendUrl
        OPS_API_BASE_URL = $apiBaseUrl
        OPS_GYM_SLUG = $authContext.Identity.gym_slug
        OPS_EMAIL = $authContext.Identity.email
        OPS_PASSWORD = $authContext.Identity.password
        OPS_MEMBER_NAME = $memberName
        OPS_UPDATED_MEMBER_NAME = $updatedMemberName
    }

    Push-Location $script:FrontendDir
    try {
        foreach ($key in $browserEnv.Keys) {
            Set-Item -Path "Env:$key" -Value $browserEnv[$key]
        }

        $browserInstall = Invoke-External -Command "npm" -Arguments @("exec", "playwright", "install", "chromium") -WorkingDirectory $script:FrontendDir
        Save-Artifact -Name "browser\playwright-install.txt" -Content $browserInstall.Output | Out-Null

        try {
            $browserRun = Invoke-External -Command "node" -Arguments @($browserScript) -WorkingDirectory $script:FrontendDir
            Save-Artifact -Name "browser\playwright-run.txt" -Content $browserRun.Output | Out-Null
        }
        catch {
            Save-Artifact -Name "browser\playwright-run.txt" -Content $_.Exception.Message | Out-Null
            if (Test-Path (Join-Path $script:RunDir "browser\browser-results.json")) {
                $script:Summary.browser = Read-BrowserResult
            }
            throw
        }
    }
    finally {
        foreach ($key in $browserEnv.Keys) {
            Remove-Item -Path "Env:$key" -ErrorAction SilentlyContinue
        }
        Pop-Location
    }

    $browserResult = Read-BrowserResult
    $script:Summary.browser = $browserResult
    $script:Summary.checks.browser_flow = $true

    Write-Step "Verifying persisted member state through the API"
    $searchTerm = [System.Uri]::EscapeDataString($updatedMemberName)
    $membersResponse = Invoke-JsonRequest -Method "GET" -Url "$apiBaseUrl/api/v1/members/?page=1&page_size=20&search=$searchTerm" -Headers $authHeaders
    Save-Artifact -Name "members-search.json" -Content ($membersResponse | ConvertTo-Json -Depth 10) | Out-Null
    $matchingMember = $membersResponse.items | Where-Object { $_.full_name -eq $updatedMemberName } | Select-Object -First 1
    if (-not $matchingMember) {
        throw "Could not find the updated member '$updatedMemberName' through the API."
    }
    $script:Summary.checks.member_api_verification = $true

    $summaryJson = $script:Summary | ConvertTo-Json -Depth 10
    Save-Artifact -Name "summary.json" -Content $summaryJson | Out-Null

    Write-Host ""
    Write-Host "Operational validation completed successfully." -ForegroundColor Green
    Write-Host "Artifacts: $script:RunDir"
    exit 0
}
catch {
    Save-PartialDiagnostics
    $script:Summary.error = $_.Exception.Message
    $summaryJson = $script:Summary | ConvertTo-Json -Depth 10
    Save-Artifact -Name "summary.json" -Content $summaryJson | Out-Null

    Write-Host ""
    Write-Host "Operational validation failed." -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Artifacts: $script:RunDir"
    exit 1
}
