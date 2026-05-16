param(
    [Parameter(Position = 0)]
    [ValidateSet("version", "doctor", "init-codex", "route", "testgaps", "mcp-start")]
    [string]$Command = "version",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$externalRuflo = "C:\aigymos\external\ruflo"

function Invoke-Ruflo {
    param([string[]]$RufloArgs)

    Push-Location $repoRoot
    try {
        & npx.cmd ruflo@latest @RufloArgs
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $externalRuflo)) {
    Write-Warning "Ruflo clone not found at $externalRuflo. Clone it first: git clone https://github.com/ruvnet/ruflo $externalRuflo"
}

switch ($Command) {
    "version" {
        Invoke-Ruflo @("--version")
    }
    "doctor" {
        Invoke-Ruflo @("doctor")
    }
    "init-codex" {
        Write-Host "This initializes Ruflo for Codex in the current repository. Review generated files before committing." -ForegroundColor Yellow
        Invoke-Ruflo @("init", "--codex")
    }
    "route" {
        $task = ($Args -join " ").Trim()
        if (-not $task) {
            throw "Provide a task description. Example: .\scripts\ruflo-dev.ps1 route `"fix task queue bug`""
        }
        Invoke-Ruflo @("hooks", "route", $task, "--include-explanation")
    }
    "testgaps" {
        Invoke-Ruflo @("hooks", "coverage-gaps", "--format", "table", "--limit", "20")
    }
    "mcp-start" {
        Invoke-Ruflo @("mcp", "start")
    }
}

