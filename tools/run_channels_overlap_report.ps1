\
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

try {
  Write-Log "START channels overlap report"
  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python = $python"
  & $python (Join-Path $repo "tools\channels_overlap_report.py")
  if ($LASTEXITCODE -ne 0) { throw "Report failed ($LASTEXITCODE)" }
  Write-Log "DONE"
}
catch {
  Write-Log "ERROR: $($_.Exception.Message)"
  throw
}
finally {
  Read-Host "Press Enter to close"
}
