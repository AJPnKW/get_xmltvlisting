#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
  param([string]$Msg)
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[$ts] $Msg"
}

$repo = Split-Path -Parent $PSScriptRoot

# Use latest out\downloads\<timestamp>\ by default
$downloadsRoot = Join-Path $repo "out\downloads"
if (-not (Test-Path $downloadsRoot)) { throw "Missing downloads root: $downloadsRoot" }

$latestDownloads = Get-ChildItem -LiteralPath $downloadsRoot -Directory |
  Sort-Object Name -Descending |
  Select-Object -First 1

if (-not $latestDownloads) { throw "No downloads folders found under: $downloadsRoot" }

$inputDir = $latestDownloads.FullName
$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$outRoot = Join-Path $repo "out\analysis"
$outDir = Join-Path $outRoot $stamp
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$log = Join-Path $outDir ("run_channels_analysis_{0}.log.txt" -f $stamp)
Start-Transcript -Path $log -Force | Out-Null

try {
  Write-Log "START channels overlap analysis"
  Write-Log "Repo     = $repo"
  Write-Log "InputDir = $inputDir"
  Write-Log "OutDir   = $outDir"

  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python   = $python"

  $script = Join-Path $repo "tools\analyze_channels_overlap.py"
  if (-not (Test-Path $script)) { throw "Missing script: $script" }

  $args = @($script, "--input_dir", $inputDir, "--out_dir", $outDir)
  Write-Log "Running: python $($args -join ' ')"
  & $python @args
  if ($LASTEXITCODE -ne 0) { throw "Analyzer failed with exit code $LASTEXITCODE" }

  Write-Log "DONE"
}
catch {
  Write-Log "ERROR: $($_.Exception.Message)"
  throw
}
finally {
  Stop-Transcript | Out-Null
  Write-Host ""
  Write-Host "Outputs:"
  Write-Host "  $outDir"
  Write-Host "Log:"
  Write-Host "  $log"
  Write-Host ""
  Read-Host "Press Enter to close"
}
