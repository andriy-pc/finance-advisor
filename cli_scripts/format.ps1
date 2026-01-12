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

# isort
isort `
    --quiet `
    --settings "$ProjectRoot\pyproject.toml" `
    --skip "$ProjectRoot\.cache" `
    --skip "$ProjectRoot\.venv" `
    @CheckArgs `
    "$ProjectRoot"

# black
black `
    @CheckArgs `
    "$ProjectRoot"

# mypy
mypy `
    --config-file "$ProjectRoot\pyproject.toml" `
    --cache-dir "$ProjectRoot\.mypy_cache" `
    "$ProjectRoot"
