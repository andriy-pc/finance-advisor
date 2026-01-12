#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."

# Activate virtual environment if it exists
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    . $VenvActivate
}

# Default minimum coverage
$MinCoverage = 80

# Parse arguments
foreach ($arg in $args) {
    if ($arg -like "--min-coverage=*") {
        $value = $arg.Split("=", 2)[1]

        if (-not ($value -match '^\d+$') -or
            [int]$value -lt 0 -or
            [int]$value -gt 100) {
            Write-Error "Error: min-coverage must be a number between 0 and 100"
            exit 1
        }

        $MinCoverage = [int]$value
    }
}

Write-Host "`nRunning tests"
Push-Location $ProjectRoot
pytest tests -svv `
    --disable-warnings `
    --cov-fail-under=$MinCoverage `
    --cov="$ProjectRoot" `
    --cov-config="$ProjectRoot\pyproject.toml"
Pop-Location

Write-Host "`nXML coverage report"
Push-Location $ProjectRoot
coverage xml
Pop-Location

Write-Host "`nHTML coverage report"
Push-Location $ProjectRoot
coverage html
Pop-Location
