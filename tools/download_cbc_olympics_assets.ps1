# FILE: tools/download_cbc_olympics_assets.ps1
# VERSION: 1
# UPDATED: 2026-02-13T00:00:00Z
# CHANGE NOTES:
# - Creates local CBC/Olympics asset folders.
# - Downloads CBC logo when reachable.
# - Generates deterministic local SVG placeholders for all required icons and background texture.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$cbcDir = Join-Path $repoRoot 'assets/cbc'
$olyDir = Join-Path $repoRoot 'assets/olympics'

New-Item -ItemType Directory -Force -Path $cbcDir | Out-Null
New-Item -ItemType Directory -Force -Path $olyDir | Out-Null

function Write-Utf8NoBom {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Content
  )
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function New-SvgChannelIcon {
  param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter(Mandatory=$true)][string]$City,
    [Parameter(Mandatory=$true)][string]$Callsign
  )

  $safeCity = [System.Security.SecurityElement]::Escape($City)
  $safeCall = [System.Security.SecurityElement]::Escape($Callsign)

  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256' role='img' aria-label='CBC $safeCity'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='#d9001b'/>
      <stop offset='100%' stop-color='#7a000f'/>
    </linearGradient>
  </defs>
  <rect width='256' height='256' rx='34' fill='url(#g)'/>
  <rect x='14' y='14' width='228' height='228' rx='26' fill='none' stroke='rgba(255,255,255,.35)' stroke-width='2'/>
  <text x='128' y='112' text-anchor='middle' font-size='34' font-family='Segoe UI, Arial, sans-serif' font-weight='700' fill='#ffffff'>CBC</text>
  <text x='128' y='154' text-anchor='middle' font-size='24' font-family='Segoe UI, Arial, sans-serif' font-weight='700' fill='#ffe9ed'>$safeCity</text>
  <text x='128' y='186' text-anchor='middle' font-size='17' font-family='Consolas, monospace' fill='#fff5f7'>$safeCall</text>
</svg>
"@
  Write-Utf8NoBom -Path $FilePath -Content $svg
}

function New-CbcLogoSvg {
  param([Parameter(Mandatory=$true)][string]$FilePath)
  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256' role='img' aria-label='CBC'>
  <rect width='256' height='256' rx='34' fill='#d9001b'/>
  <circle cx='128' cy='128' r='76' fill='none' stroke='#ffffff' stroke-width='20'/>
  <circle cx='128' cy='128' r='34' fill='#ffffff'/>
</svg>
"@
  Write-Utf8NoBom -Path $FilePath -Content $svg
}

function New-OlympicsTexture {
  param([Parameter(Mandatory=$true)][string]$FilePath)
  $svg = @"
<svg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080' viewBox='0 0 1920 1080' preserveAspectRatio='xMidYMid slice'>
  <defs>
    <linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0%' stop-color='#0a1424'/>
      <stop offset='100%' stop-color='#050912'/>
    </linearGradient>
    <pattern id='snow' width='120' height='120' patternUnits='userSpaceOnUse'>
      <circle cx='14' cy='16' r='1.2' fill='rgba(255,255,255,.18)'/>
      <circle cx='56' cy='42' r='1.3' fill='rgba(255,255,255,.14)'/>
      <circle cx='92' cy='78' r='1.1' fill='rgba(255,255,255,.16)'/>
      <circle cx='38' cy='96' r='1.0' fill='rgba(255,255,255,.12)'/>
    </pattern>
  </defs>
  <rect width='1920' height='1080' fill='url(#sky)'/>
  <path d='M0,860 C230,760 400,940 620,840 C790,760 940,900 1110,820 C1320,720 1560,900 1920,780 L1920,1080 L0,1080 Z' fill='rgba(255,255,255,.07)'/>
  <path d='M0,930 C240,860 420,1010 640,910 C860,820 980,1010 1210,900 C1420,810 1640,1010 1920,890 L1920,1080 L0,1080 Z' fill='rgba(255,255,255,.09)'/>
  <rect width='1920' height='1080' fill='url(#snow)'/>
</svg>
"@
  Write-Utf8NoBom -Path $FilePath -Content $svg
}

$logoPath = Join-Path $cbcDir 'cbc-logo.svg'
$logoDownloaded = $false
$logoCandidates = @(
  'https://upload.wikimedia.org/wikipedia/commons/6/67/CBC_Logo_1992-Present.svg',
  'https://upload.wikimedia.org/wikipedia/commons/f/fd/Canadian_Broadcasting_Corporation_logo.svg'
)

foreach ($url in $logoCandidates) {
  try {
    Invoke-WebRequest -Uri $url -OutFile $logoPath -TimeoutSec 20
    if ((Test-Path $logoPath) -and ((Get-Item $logoPath).Length -gt 0)) {
      $logoDownloaded = $true
      Write-Host "Downloaded CBC logo from $url"
      break
    }
  }
  catch {
    Write-Host "Logo download failed from $url"
  }
}

if (-not $logoDownloaded) {
  New-CbcLogoSvg -FilePath $logoPath
  Write-Host 'Generated local placeholder: cbc-logo.svg'
}

$channels = @(
  @{ File='cbc-toronto.svg'; City='Toronto'; Callsign='CBLT-DT' },
  @{ File='cbc-vancouver.svg'; City='Vancouver'; Callsign='CBUT-DT' },
  @{ File='cbc-halifax.svg'; City='Halifax'; Callsign='CBHT-DT' },
  @{ File='cbc-winnipeg.svg'; City='Winnipeg'; Callsign='CBWT-DT' },
  @{ File='cbc-calgary.svg'; City='Calgary'; Callsign='CBRT-DT' }
)

foreach ($ch in $channels) {
  $path = Join-Path $cbcDir $ch.File
  New-SvgChannelIcon -FilePath $path -City $ch.City -Callsign $ch.Callsign
  Write-Host "Wrote $($ch.File)"
}

New-OlympicsTexture -FilePath (Join-Path $olyDir 'winter-texture.svg')
Write-Host 'Wrote winter-texture.svg'
Write-Host 'Asset generation complete.'
