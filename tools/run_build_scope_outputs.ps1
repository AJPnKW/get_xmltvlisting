#requires -Version 5.1
param(
    [string]$DecisionsJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = (Get-Command python -ErrorAction Stop).Path
$script = Join-Path $repo "tools\build_scope_outputs.py"
$argsList = @($script, "--iptv-dir", (Join-Path $repo "IPTV"))

if ($DecisionsJson) {
    if (-not (Test-Path $DecisionsJson)) {
        throw "Decisions JSON file not found: $DecisionsJson"
    }
    $argsList += @("--decisions", $DecisionsJson)
}

& $python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "build_scope_outputs.py failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Updated scope outputs in:"
Write-Host "  $repo\IPTV\scope_outputs"
