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
  Write-Log "START channel naming mapping"
  $python = (Get-Command python -ErrorAction Stop).Path
  Write-Log "Python = $python"

  & $python (Join-Path $repo "tools\build_channel_mapping_from_manual_review.py")
  if ($LASTEXITCODE -ne 0) { throw "Mapping builder failed ($LASTEXITCODE)" }

  & $python (Join-Path $repo "tools\apply_channel_mapping_to_channels_json.py")
  if ($LASTEXITCODE -ne 0) { throw "Mapping apply failed ($LASTEXITCODE)" }

  Write-Log "DONE"
}
catch {
  Write-Log "ERROR: $($_.Exception.Message)"
  throw
}
finally {
  Read-Host "Press Enter to close"
}
