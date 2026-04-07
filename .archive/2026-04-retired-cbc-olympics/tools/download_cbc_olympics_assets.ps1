# FILE: tools/download_cbc_olympics_assets.ps1
# VERSION: 2
# UPDATED: 2026-02-13T00:00:00Z
# CHANGE NOTES:
# - Creates required local asset folders and files for CBC/Olympics UI.
# - Attempts stable image downloads with deterministic SVG fallbacks.
# - Logs execution to out/download_cbc_olympics_assets.log.txt.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $repoRoot 'out'
$cbcDir = Join-Path $repoRoot 'assets/cbc'
$olyDir = Join-Path $repoRoot 'assets/olympics'
$logPath = Join-Path $outDir 'download_cbc_olympics_assets.log.txt'

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $cbcDir | Out-Null
New-Item -ItemType Directory -Force -Path $olyDir | Out-Null

function Write-Log {
  param([Parameter(Mandatory=$true)][string]$Message)
  $line = "[{0}] {1}" -f ([DateTime]::UtcNow.ToString('u')), $Message
  $line | Out-File -FilePath $logPath -Append -Encoding utf8
  Write-Host $line
}

function Write-Utf8NoBom {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Content
  )
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Write-CbcLogo {
  param([Parameter(Mandatory=$true)][string]$Path)
  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256' role='img' aria-label='CBC'>
  <rect width='256' height='256' rx='36' fill='#d6001c'/>
  <circle cx='128' cy='128' r='78' fill='none' stroke='#ffffff' stroke-width='20'/>
  <circle cx='128' cy='128' r='35' fill='#ffffff'/>
</svg>
"@
  Write-Utf8NoBom -Path $Path -Content $svg
}

function Write-ChannelPlaceholder {
  param([Parameter(Mandatory=$true)][string]$Path)
  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256' role='img' aria-label='CBC Channel'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='#d6001c'/>
      <stop offset='100%' stop-color='#7d0010'/>
    </linearGradient>
  </defs>
  <rect width='256' height='256' rx='34' fill='url(#g)'/>
  <text x='128' y='115' text-anchor='middle' font-size='34' font-family='Segoe UI, Arial, sans-serif' font-weight='700' fill='#ffffff'>CBC</text>
  <text x='128' y='156' text-anchor='middle' font-size='22' font-family='Segoe UI, Arial, sans-serif' font-weight='700' fill='#ffe5ea'>CHANNEL</text>
</svg>
"@
  Write-Utf8NoBom -Path $Path -Content $svg
}

function Write-ChannelLogo {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$City,
    [Parameter(Mandatory=$true)][string]$Callsign
  )

  $safeCity = [System.Security.SecurityElement]::Escape($City)
  $safeCall = [System.Security.SecurityElement]::Escape($Callsign)

  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256' role='img' aria-label='CBC $safeCity'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='#d6001c'/>
      <stop offset='100%' stop-color='#870011'/>
    </linearGradient>
  </defs>
  <rect width='256' height='256' rx='34' fill='url(#g)'/>
  <rect x='16' y='16' width='224' height='224' rx='24' fill='none' stroke='rgba(255,255,255,.3)' stroke-width='2'/>
  <text x='128' y='108' text-anchor='middle' font-size='34' font-family='Segoe UI, Arial, sans-serif' font-weight='700' fill='#ffffff'>CBC</text>
  <text x='128' y='147' text-anchor='middle' font-size='24' font-family='Segoe UI, Arial, sans-serif' font-weight='700' fill='#ffe6ea'>$safeCity</text>
  <text x='128' y='180' text-anchor='middle' font-size='16' font-family='Consolas, monospace' fill='#fff8fa'>$safeCall</text>
</svg>
"@

  Write-Utf8NoBom -Path $Path -Content $svg
}

function Write-WinterPattern {
  param([Parameter(Mandatory=$true)][string]$Path)
  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080' viewBox='0 0 1920 1080' preserveAspectRatio='xMidYMid slice'>
  <defs>
    <linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0%' stop-color='#0a1426'/>
      <stop offset='100%' stop-color='#050a13'/>
    </linearGradient>
    <pattern id='snow' width='130' height='130' patternUnits='userSpaceOnUse'>
      <circle cx='18' cy='20' r='1.2' fill='rgba(255,255,255,.2)'/>
      <circle cx='68' cy='42' r='1.1' fill='rgba(255,255,255,.16)'/>
      <circle cx='104' cy='84' r='1.4' fill='rgba(255,255,255,.15)'/>
      <circle cx='42' cy='102' r='1.1' fill='rgba(255,255,255,.13)'/>
    </pattern>
  </defs>
  <rect width='1920' height='1080' fill='url(#sky)'/>
  <path d='M0,860 C220,760 420,945 620,840 C820,740 980,950 1180,842 C1380,748 1640,940 1920,800 L1920,1080 L0,1080 Z' fill='rgba(255,255,255,.08)'/>
  <path d='M0,930 C200,850 450,1020 650,930 C870,830 1020,1030 1230,932 C1450,830 1700,1010 1920,900 L1920,1080 L0,1080 Z' fill='rgba(255,255,255,.11)'/>
  <rect width='1920' height='1080' fill='url(#snow)'/>
</svg>
"@
  Write-Utf8NoBom -Path $Path -Content $svg
}

function Try-Download {
  param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$Path
  )
  try {
    Invoke-WebRequest -Uri $Url -OutFile $Path -TimeoutSec 25
    if ((Test-Path $Path) -and ((Get-Item $Path).Length -gt 0)) {
      return $true
    }
    return $false
  }
  catch {
    return $false
  }
}

Write-Log 'Starting CBC/Olympics asset sync.'

$cbcLogoPath = Join-Path $cbcDir 'cbc_logo.svg'
$placeholderPath = Join-Path $cbcDir 'channel_placeholder.svg'
$winterPatternPath = Join-Path $olyDir 'bg_winter.svg'
$winterPhotoPath = Join-Path $olyDir 'bg_winter_photo.jpg'

$logoUrls = @(
  'https://upload.wikimedia.org/wikipedia/commons/6/67/CBC_Logo_1992-Present.svg',
  'https://upload.wikimedia.org/wikipedia/commons/f/fd/Canadian_Broadcasting_Corporation_logo.svg'
)

$logoOk = $false
foreach ($url in $logoUrls) {
  Write-Log "Trying logo download: $url"
  if (Try-Download -Url $url -Path $cbcLogoPath) {
    $logoOk = $true
    Write-Log 'Downloaded cbc_logo.svg'
    break
  }
}

if (-not $logoOk) {
  Write-CbcLogo -Path $cbcLogoPath
  Write-Log 'Generated fallback cbc_logo.svg'
}

Write-ChannelPlaceholder -Path $placeholderPath
Write-Log 'Generated channel_placeholder.svg'

$channels = @(
  @{ File='cbc_toronto.svg'; City='Toronto'; Callsign='CBLT-DT' },
  @{ File='cbc_vancouver.svg'; City='Vancouver'; Callsign='CBUT-DT' },
  @{ File='cbc_halifax.svg'; City='Halifax'; Callsign='CBHT-DT' },
  @{ File='cbc_winnipeg.svg'; City='Winnipeg'; Callsign='CBWT-DT' },
  @{ File='cbc_calgary.svg'; City='Calgary'; Callsign='CBRT-DT' }
)

foreach ($ch in $channels) {
  $p = Join-Path $cbcDir $ch.File
  Write-ChannelLogo -Path $p -City $ch.City -Callsign $ch.Callsign
  Write-Log "Generated $($ch.File)"
}

Write-WinterPattern -Path $winterPatternPath
Write-Log 'Generated bg_winter.svg'

$photoUrl = 'https://upload.wikimedia.org/wikipedia/commons/8/88/Lake_Louise_17092005.jpg'
Write-Log "Trying winter photo download: $photoUrl"
if (Try-Download -Url $photoUrl -Path $winterPhotoPath) {
  Write-Log 'Downloaded bg_winter_photo.jpg'
} else {
  if (Test-Path $winterPhotoPath) {
    Remove-Item -Force $winterPhotoPath
  }
  Write-Log 'Skipped bg_winter_photo.jpg (download unavailable)'
}

Write-Log 'Asset sync complete.'
