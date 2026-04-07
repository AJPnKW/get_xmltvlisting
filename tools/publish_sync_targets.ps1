param(
    [string]$Branch = "main",
    [string]$GitHubRemote = "origin",
    [string]$HpHost = "theboys-hp290",
    [string]$HpSyncScript = "/home/andrew/bin/hp920_sync_from_github.sh",
    [switch]$SkipGitHub,
    [switch]$SkipHp920
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$serverSyncLocal = Join-Path $PSScriptRoot "server\hp920_sync_from_github.sh"

function Invoke-Git {
    param([string[]]$GitArgs)
    & git -C $repoRoot @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git -C $repoRoot $($GitArgs -join ' ')"
    }
}

function Invoke-CheckedCommand {
    param([string]$FilePath, [string[]]$CommandArgs)
    & $FilePath @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "command failed: $FilePath $($CommandArgs -join ' ')"
    }
}

function Expand-LocalEpgAssets {
    param([string]$IptvDir)
    Get-ChildItem -Path $IptvDir -Filter "EPG_*.xml.gz" -File | ForEach-Object {
        $xmlPath = $_.FullName -replace "\.gz$", ""
        Write-Host "Refreshing local $([System.IO.Path]::GetFileName($xmlPath)) from $($_.Name)"
        $inputStream = [System.IO.File]::OpenRead($_.FullName)
        try {
            $gzipStream = New-Object System.IO.Compression.GzipStream($inputStream, [System.IO.Compression.CompressionMode]::Decompress)
            try {
                $outputStream = [System.IO.File]::Create($xmlPath)
                try {
                    $gzipStream.CopyTo($outputStream)
                }
                finally {
                    $outputStream.Dispose()
                }
            }
            finally {
                $gzipStream.Dispose()
            }
        }
        finally {
            $inputStream.Dispose()
        }
    }
}

Write-Host "Repo root: $repoRoot"
Write-Host "Branch: $Branch"

$currentBranch = (& git -C $repoRoot branch --show-current).Trim()
if ($currentBranch -ne $Branch) {
    throw "Current branch is '$currentBranch'. Switch to '$Branch' before publishing."
}

if (-not $SkipHp920) {
    Write-Host "Installing HP920 GitHub sync helper"
    Invoke-CheckedCommand -FilePath "ssh" -CommandArgs @($HpHost, "mkdir -p ~/bin ~/sites/iptv-sync")
    Invoke-CheckedCommand -FilePath "scp" -CommandArgs @($serverSyncLocal, "${HpHost}:${HpSyncScript}")
    Invoke-CheckedCommand -FilePath "ssh" -CommandArgs @($HpHost, "chmod +x '$HpSyncScript'")
}

if (-not $SkipGitHub) {
    Write-Host "Pushing to GitHub remote '$GitHubRemote'"
    Invoke-Git -GitArgs @("push", $GitHubRemote, $Branch)
}

Write-Host "Refreshing local plain XML files from compressed EPG assets"
Expand-LocalEpgAssets -IptvDir (Join-Path $repoRoot "IPTV")

if (-not $SkipHp920) {
    Write-Host "Refreshing HP920 clone and LAN publish directory"
    Invoke-CheckedCommand -FilePath "ssh" -CommandArgs @($HpHost, "BRANCH='$Branch' '$HpSyncScript'")
}

Write-Host ""
Write-Host "Expected URLs after publish:"
Write-Host "GitHub folder: https://github.com/AJPnKW/get_xmltvlisting/tree/main/IPTV"
Write-Host "HP920 LAN root: http://192.168.1.73:8011/iptv-epg/"
Write-Host "HP920 reference page: http://192.168.1.73:8011/iptv-epg/IPTV_EPG_Reference.html"
