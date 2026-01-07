#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- CONFIG (keep this simple) ---
$base_lineup_id = "9330"   # base lineup: KEEP ALL, REMOVE NONE
# ---------------------------------

function Write-Log {
  param([string]$Msg)
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[$ts] $Msg"
}

function Get-LatestAnalysisFolder {
  param([string]$repo)
  $root = Join-Path $repo "out\analysis"
  if (-not (Test-Path $root)) { return $null }

  $dirs = Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending

  foreach ($d in $dirs) {
    $has = Get-ChildItem -LiteralPath $d.FullName -File -Filter "unique_channels_*.csv" -ErrorAction SilentlyContinue
    if ($has -and $has.Count -gt 0) { return $d.FullName }
  }
  return $null
}

function Load-UniqueIds {
  param([string]$analysisDir, [string]$lineupId)

  $p = Join-Path $analysisDir ("unique_channels_{0}.csv" -f $lineupId)
  if (-not (Test-Path $p)) { return @{} }

  $set = @{}
  Import-Csv -LiteralPath $p | ForEach-Object {
    if ($_.channel_id) { $set[$_.channel_id] = $true }
  }
  return $set
}

function Parse-ChannelsFromXml {
  param([string]$xmlPath)

  # Returns hashtable: channel_id -> display_name (best available)
  # NOTE: simple XML parsing; fine for channel list size.
  [xml]$x = Get-Content -LiteralPath $xmlPath

  $map = @{}
  foreach ($ch in $x.tv.channel) {
    $id = [string]$ch.id
    if (-not $id) { continue }

    # display-name can appear multiple times; choose first non-empty
    $name = ""
    foreach ($dn in $ch.'display-name') {
      if ($dn -and ([string]$dn).Trim().Length -gt 0) { $name = ([string]$dn).Trim(); break }
    }
    $map[$id] = $name
  }
  return $map
}

# ---------- MAIN ----------
$repo = Split-Path -Parent $PSScriptRoot
$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")

$outRoot = Join-Path $repo "out\reports"
$outDir  = Join-Path $outRoot $stamp
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$log = Join-Path $outDir ("build_keep_remove_report_{0}.log.txt" -f $stamp)
Start-Transcript -Path $log -Force | Out-Null

try {
  Write-Log "START keep/remove report"
  Write-Log "Repo  = $repo"
  Write-Log "OutDir= $outDir"

  $sampleDir = Join-Path $repo "sample_download_XML.TV.Listings"
  if (-not (Test-Path $sampleDir)) { throw "Missing folder: $sampleDir" }

  $xmlFiles = Get-ChildItem -LiteralPath $sampleDir -File -Filter "xmltv-*.xml" | Sort-Object Name
  if (-not $xmlFiles -or $xmlFiles.Count -lt 1) { throw "No xmltv-*.xml files found in: $sampleDir" }

  $analysisDir = Get-LatestAnalysisFolder -repo $repo
  if (-not $analysisDir) {
    throw "No analysis folder found with unique_channels_*.csv under: $repo\out\analysis\*"
  }
  Write-Log "Using analysis folder: $analysisDir"

  $reportPath = Join-Path $outDir ("keep_remove_report_{0}.txt" -f $stamp)

  $sb = New-Object System.Text.StringBuilder
  $null = $sb.AppendLine("KEEP / REMOVE REPORT")
  $null = $sb.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
  $null = $sb.AppendLine("Base lineup (KEEP ALL): $base_lineup_id")
  $null = $sb.AppendLine("")

  for ($i=0; $i -lt $xmlFiles.Count; $i++) {
    $f = $xmlFiles[$i]
    $pct = [int](($i / [double]$xmlFiles.Count) * 100)
    Write-Progress -Activity "Building keep/remove report" -Status $f.Name -PercentComplete $pct

    $m = [regex]::Match($f.Name, "^xmltv-(\d+)\.xml$", "IgnoreCase")
    $lineupId = if ($m.Success) { $m.Groups[1].Value } else { $f.BaseName }

    $channels = Parse-ChannelsFromXml -xmlPath $f.FullName   # id -> name
    $allIds = $channels.Keys

    $null = $sb.AppendLine("============================================================")
    $null = $sb.AppendLine("FILE: $($f.Name)")
    $null = $sb.AppendLine("LINEUP ID: $lineupId")
    $null = $sb.AppendLine("TOTAL CHANNELS: $($allIds.Count)")
    $null = $sb.AppendLine("")

    if ($lineupId -eq $base_lineup_id) {
      $null = $sb.AppendLine("KEEP (BASE LINEUP): ALL ($($allIds.Count))")
      $null = $sb.AppendLine("REMOVE: NONE")
      $null = $sb.AppendLine("")
      continue
    }

    $keepSet = Load-UniqueIds -analysisDir $analysisDir -lineupId $lineupId
    $keepIds = @($allIds | Where-Object { $keepSet.ContainsKey($_) })
    $removeIds = @($allIds | Where-Object { -not $keepSet.ContainsKey($_) })

    # Sort lists by display name (fallback to id)
    $keepSorted = $keepIds | Sort-Object { if ($channels[$_] -and $channels[$_].Trim().Length -gt 0) { $channels[$_] } else { $_ } }
    $removeSorted = $removeIds | Sort-Object { if ($channels[$_] -and $channels[$_].Trim().Length -gt 0) { $channels[$_] } else { $_ } }

    $null = $sb.AppendLine("KEEP (UNIQUE ONLY): $($keepSorted.Count)")
    $null = $sb.AppendLine("------------------------------------------------------------")
    foreach ($id in $keepSorted) {
      $name = $channels[$id]
      if (-not $name) { $name = "" }
      $null = $sb.AppendLine(("  - {0} [{1}]" -f $name, $id).TrimEnd())
    }
    if ($keepSorted.Count -eq 0) { $null = $sb.AppendLine("  (none)") }

    $null = $sb.AppendLine("")
    $null = $sb.AppendLine("REMOVE (DUPLICATES): $($removeSorted.Count)")
    $null = $sb.AppendLine("------------------------------------------------------------")
    foreach ($id in $removeSorted) {
      $name = $channels[$id]
      if (-not $name) { $name = "" }
      $null = $sb.AppendLine(("  - {0} [{1}]" -f $name, $id).TrimEnd())
    }
    if ($removeSorted.Count -eq 0) { $null = $sb.AppendLine("  (none)") }

    $null = $sb.AppendLine("")
  }

  [System.IO.File]::WriteAllText($reportPath, $sb.ToString(), [System.Text.Encoding]::UTF8)

  Write-Progress -Activity "Building keep/remove report" -Completed
  Write-Log "DONE"
  Write-Host ""
  Write-Host "Report:"
  Write-Host "  $reportPath"
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
