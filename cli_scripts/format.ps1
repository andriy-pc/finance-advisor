#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."

# Activate virtual environment if it exists
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    . $VenvActivate
}

# Optional arguments (equivalent to ${check_args[@]})
# These come from arguments passed to the script
$CheckArgs = $args

Write-Host "Running isort..."
python -m isort `
    --quiet `
    --settings "$ProjectRoot\pyproject.toml" `
    @CheckArgs `
    "$ProjectRoot"

Write-Host "Running black..."
python -m black `
    --config "$ProjectRoot\pyproject.toml" `
    @CheckArgs `
    "$ProjectRoot"

Write-Host "Running mypy..."
python -m mypy `
    --config-file "$ProjectRoot\pyproject.toml" `
    --cache-dir "$ProjectRoot\.mypy_cache" `
    "$ProjectRoot"
