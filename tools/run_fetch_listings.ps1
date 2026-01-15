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

$publishDir = Join-Path $repo "IPTV"
New-Item -ItemType Directory -Force -Path $publishDir | Out-Null

$log = Join-Path $outDir ("run_fetch_listings_{0}.log.txt" -f $stamp)
Start-Transcript -Path $log -Force | Out-Null

try {
  Write-Log "START fetch listings (audit + repo publish)"
  Write-Log "Repo       = $repo"
  Write-Log "OutDir      = $outDir"
  Write-Log "PublishDir  = $publishDir"
  Write-Log "Lineups     = 10269 10270 10271 10272 10273"
  Write-Log "Days/Offset = 7/0"
  Write-Log "Mode        = all_or_nothing"

  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python     = $python"

  $script = Join-Path $repo "tools\fetch_xmltvlistings_listings.py"
  if (-not (Test-Path $script)) { throw "Missing script: $script" }

  & $python $script --lineups 10269 10270 10271 10272 10273 --days 7 --offset 0 --out-dir $outDir --publish-dir $publishDir --publish-mode all_or_nothing
  $exit = $LASTEXITCODE

  if ($exit -eq 0) {
    Write-Log "DONE (all lineups updated + published)"
  } elseif ($exit -eq 2) {
    Write-Log "DONE (blocked/partial; publish unchanged; audit may contain partial backups)"
  } else {
    throw "Fetcher failed with exit code $exit"
  }

  Write-Host ""
  Write-Host "Audit outputs:"
  Write-Host "  $outDir"
  Write-Host "Repo publish outputs (push these to GitHub):"
  Write-Host "  $publishDir"
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
