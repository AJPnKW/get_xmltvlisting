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
$outRoot = Join-Path $repo "out\analysis"
$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$outDir = Join-Path $outRoot $stamp
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# dated log file name (your request)
$log = Join-Path $outDir ("run_local_analysis_{0}.log.txt" -f $stamp)
Start-Transcript -Path $log -Force | Out-Null

try {
  Write-Log "START local XMLTV overlap analysis"
  Write-Log "Repo = $repo"
  Write-Log "OutDir = $outDir"

  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python = $python"

  $sampleDir = Join-Path $repo "sample_download_XML.TV.Listings"
  if (-not (Test-Path $sampleDir)) { throw "Missing folder: $sampleDir" }

  $xml = Get-ChildItem -LiteralPath $sampleDir -File -Filter "xmltv-*.xml" | Sort-Object Name
  if (-not $xml -or $xml.Count -lt 1) { throw "No xmltv-*.xml files found in: $sampleDir" }

  $analyzer = Join-Path $repo "src\get_xmltvlisting\xmltv_analyze.py"
  if (-not (Test-Path $analyzer)) { throw "Missing analyzer: $analyzer" }

  $args = @(
    $analyzer,
    "--input_dir", $sampleDir,
    "--out_dir",  $outDir
  )

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
