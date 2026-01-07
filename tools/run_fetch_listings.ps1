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

$deviceDir = $env:IPTV_LINEUP_DIR
if ([string]::IsNullOrWhiteSpace($deviceDir)) {
  $deviceDir = "C:\X1_Share\Tivimate\iptv_lineup"
}
New-Item -ItemType Directory -Force -Path $deviceDir | Out-Null

$publishDir = Join-Path $repo "IPTV\iptv_lineup"
New-Item -ItemType Directory -Force -Path $publishDir | Out-Null

$log = Join-Path $outDir ("run_fetch_listings_{0}.log.txt" -f $stamp)
Start-Transcript -Path $log -Force | Out-Null

try {
  Write-Log "START fetch listings (audit + device + repo publish)"
  Write-Log "Repo       = $repo"
  Write-Log "OutDir      = $outDir"
  Write-Log "DeviceDir   = $deviceDir"
  Write-Log "PublishDir  = $publishDir"

  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python     = $python"

  $script = Join-Path $repo "tools\fetch_xmltvlistings_listings.py"
  if (-not (Test-Path $script)) { throw "Missing script: $script" }

  & $python $script --lineups 9329 9330 9331 --days 7 --offset 0 --out-dir $outDir --device-dir $deviceDir --repo-publish-dir $publishDir
  $exit = $LASTEXITCODE

  if ($exit -eq 0) {
    Write-Log "DONE (all lineups updated)"
  } elseif ($exit -eq 2) {
    Write-Log "DONE (partial: one or more lineups skipped due to limit/invalid/error; existing files preserved)"
  } else {
    throw "Fetcher failed with exit code $exit"
  }

  Write-Host ""
  Write-Host "Audit outputs:"
  Write-Host "  $outDir"
  Write-Host "Repo publish outputs (push these to GitHub):"
  Write-Host "  $publishDir"
  Write-Host "Local device outputs (optional):"
  Write-Host "  $deviceDir"
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
