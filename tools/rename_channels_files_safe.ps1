\
#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$iptv = Join-Path $repo "IPTV"

$map = @{
  "Rogers_Toronto_ON[CA]-channels-10270.xml"          = "Rogers_Toronto_ON_CA_channels_10270.xml"
  "Telus_Optik_Vancouver_BC[CA]-channels-10269.xml"   = "Telus_Optik_Vancouver_BC_CA_channels_10269.xml"
  "Xfinity_Chicago_IL[US]-channels-10271.xml"         = "Xfinity_Chicago_IL_US_channels_10271.xml"
  "Verizon_FIOS_NewYork_NY[US]-channels-10273.xml"    = "Verizon_FIOS_NewYork_NY_US_channels_10273.xml"
  "Broadcast_LosAngeles_CA[US]-channels-10272.xml"    = "Broadcast_LosAngeles_CA_US_channels_10272.xml"
}

Write-Host "IPTV: $iptv"
foreach ($old in $map.Keys) {
  $src = Join-Path $iptv $old
  $dstName = $map[$old]
  $dst = Join-Path $iptv $dstName
  if (Test-Path $src) {
    if (-not (Test-Path $dst)) {
      Rename-Item -LiteralPath $src -NewName $dstName
      Write-Host "Renamed: $old -> $dstName"
    } else {
      Write-Host "Skip (target exists): $dstName"
    }
  } else {
    Write-Host "Skip (missing): $old"
  }
}
