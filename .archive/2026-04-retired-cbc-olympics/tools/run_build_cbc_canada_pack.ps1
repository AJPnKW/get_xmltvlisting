# FILE: tools/run_build_cbc_canada_pack.ps1
# VERSION: 1.0.0
# UPDATED: 2026-02-12T00:00:00Z
# CHANGE NOTES:
# - Adds wrapper to run CBC Canada pack builder with transcript logging.
# - Supports optional source M3U override while defaulting to IPTV/cbc_canada.m3u.

#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
  param([string]$Msg)
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[$ts] $Msg"
}

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$outDir = Join-Path $repo ("out\downloads\{0}" -f $stamp)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$log = Join-Path $outDir ("run_build_cbc_canada_pack_{0}.log.txt" -f $stamp)
Start-Transcript -Path $log -Force | Out-Null

try {
  Write-Log "START build CBC Canada pack"
  Write-Log "Repo      = $repo"
  Write-Log "OutDir    = $outDir"

  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python    = $python"

  $script = Join-Path $repo "tools\build_cbc_canada_pack.py"
  if (-not (Test-Path $script)) { throw "Missing script: $script" }

  $sourceM3U = if ($env:CBC_PACK_SOURCE_M3U) { $env:CBC_PACK_SOURCE_M3U } else { "IPTV/cbc_canada.m3u" }
  Write-Log "SourceM3U = $sourceM3U"

  & $python $script --iptv-dir "IPTV" --source-m3u $sourceM3U
  $exit = $LASTEXITCODE
  if ($exit -ne 0) { throw "CBC pack builder failed with exit code $exit" }

  Write-Log "DONE CBC pack builder"
  Write-Host ""
  Write-Host "Produced:"
  Write-Host "  $repo\IPTV\CBC_Canada.m3u"
  Write-Host "  $repo\IPTV\CBC_Canada.xml"
  Write-Host "Log:"
  Write-Host "  $log"
  Write-Host ""
}
catch {
  Write-Log "ERROR: $($_.Exception.Message)"
  throw
}
finally {
  Stop-Transcript | Out-Null
  Read-Host "Press Enter to close"
}

