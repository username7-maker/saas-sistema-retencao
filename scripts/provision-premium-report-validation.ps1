param(
    [string]$ApiBaseUrl = "https://ai-gym-os-api-production.up.railway.app",
    [string]$OutputRoot = ".planning\\artifacts\\premium-report-validation",
    [string]$RailwayService = "ai-gym-os-api"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $repoRoot (Join-Path $OutputRoot $timestamp)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

function Invoke-ApiJson {
    param(
        [ValidateSet("GET", "POST")]
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )

    $params = @{
        Method      = $Method
        Uri         = $Url
        Headers     = $Headers
        ErrorAction = "Stop"
        TimeoutSec  = 60
    }

    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }

    return Invoke-RestMethod @params
}

function Invoke-ApiDownload {
    param(
        [string]$Url,
        [string]$OutFile,
        [hashtable]$Headers = @{}
    )

    Invoke-WebRequest -Method GET -Uri $Url -Headers $Headers -OutFile $OutFile -ErrorAction Stop -TimeoutSec 120 | Out-Null
}

$gymSuffix = Get-Date -Format "yyyyMMddHHmmss"
$gymSlug = "premium-validation-$gymSuffix"
$email = "premium.validation.$gymSuffix@example.com"
$password = "Validacao!2026"

$registerPayload = @{
    gym_name  = "Premium Validation $gymSuffix"
    gym_slug  = $gymSlug
    full_name = "Premium Validation Owner"
    email     = $email
    password  = $password
}

$null = Invoke-ApiJson -Method POST -Url "$ApiBaseUrl/api/v1/auth/register" -Body $registerPayload

$loginPayload = @{
    gym_slug = $gymSlug
    email    = $email
    password = $password
}

$loginResponse = Invoke-ApiJson -Method POST -Url "$ApiBaseUrl/api/v1/auth/login" -Body $loginPayload
$seedJson = & railway.cmd run --service $RailwayService -- powershell -Command "Set-Location saas-backend; python scripts/seed_premium_report_validation.py --gym-slug $gymSlug --owner-email $email"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to seed premium report validation data through Railway."
}
$seedResult = $seedJson | ConvertFrom-Json

$state = [ordered]@{
    run_id = $timestamp
    api_base_url = $ApiBaseUrl
    output_dir = $runDir
    credentials = [ordered]@{
        gym_slug = $gymSlug
        email = $email
        password = $password
    }
    owner = [ordered]@{
        email = $email
    }
    members = $seedResult.members
    primary_member = $seedResult.primary_member
    evaluations = $seedResult.evaluations
}

$statePath = Join-Path $runDir "validation-state.json"
$state | ConvertTo-Json -Depth 10 | Set-Content -Path $statePath -Encoding UTF8

Write-Host "Validation state written to $statePath"
