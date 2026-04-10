#requires -Version 5.1
param(
    [string]$SourceHtml = "C:\Users\andrew\PROJECTS\iptv\temp\XTENDED IPTV MASTER SECTIONS.html"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not (Test-Path $SourceHtml)) {
    throw "Source HTML file not found: $SourceHtml"
}

$python = (Get-Command python -ErrorAction Stop).Path
$script = Join-Path $repo "tools\build_extended_input_review.py"

& $python $script $SourceHtml --iptv-dir (Join-Path $repo "IPTV")
if ($LASTEXITCODE -ne 0) {
    throw "build_extended_input_review.py failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Updated:"
Write-Host "  $repo\IPTV\INPUT_SCOPE_CHANNEL_DATA.json"
Write-Host "  $repo\IPTV\INPUT_SCOPE_SOURCE_MAP.json"
Write-Host "  $repo\IPTV\INPUT_SCOPE_CHANNEL_REVIEW.html"
Write-Host "  $repo\IPTV\EXTENDED_INPUT_PARSE_REPORT.html"
