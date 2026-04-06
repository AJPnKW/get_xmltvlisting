param(
    [string]$Branch = "main",
    [string]$GitHubRemote = "origin",
    [string]$HpRemote = "hp920",
    [string]$HpHost = "theboys-hp290",
    [string]$HpRemoteRepo = "/home/andrew/repos/get_xmltvlisting.git",
    [string]$HpHookScript = "/home/andrew/bin/hp920_get_xmltvlisting_post_receive.sh",
    [switch]$SkipGitHub,
    [switch]$SkipHp920
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$serverHookLocal = Join-Path $PSScriptRoot "server\hp920_post_receive.sh"
$tempHook = Join-Path $env:TEMP "hp920-post-receive-hook.tmp"
$hpRemoteUrl = "$HpHost`:$HpRemoteRepo"

function Invoke-Git {
    param([string[]]$Args)
    & git -C $repoRoot @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git -C $repoRoot $($Args -join ' ')"
    }
}

function Invoke-CheckedCommand {
    param([string]$FilePath, [string[]]$Args)
    & $FilePath @Args
    if ($LASTEXITCODE -ne 0) {
        throw "command failed: $FilePath $($Args -join ' ')"
    }
}

Write-Host "Repo root: $repoRoot"
Write-Host "Branch: $Branch"

$currentBranch = (& git -C $repoRoot branch --show-current).Trim()
if ($currentBranch -ne $Branch) {
    throw "Current branch is '$currentBranch'. Switch to '$Branch' before publishing."
}

if (-not $SkipHp920) {
    $remoteExists = $true
    & git -C $repoRoot remote get-url $HpRemote *> $null
    if ($LASTEXITCODE -ne 0) {
        $remoteExists = $false
    }

    if (-not $remoteExists) {
        Write-Host "Adding HP920 remote '$HpRemote' => $hpRemoteUrl"
        Invoke-Git -Args @("remote", "add", $HpRemote, $hpRemoteUrl)
    }

    Write-Host "Installing HP920 post-receive deploy hook"
    Invoke-CheckedCommand -FilePath "ssh" -Args @($HpHost, "mkdir -p ~/bin ~/repos/get_xmltvlisting.git/hooks ~/sites/iptv-sync")
    Invoke-CheckedCommand -FilePath "scp" -Args @($serverHookLocal, "${HpHost}:${HpHookScript}")

    $hookContent = @"
#!/usr/bin/env bash
set -euo pipefail
exec "$HpHookScript"
"@
    Set-Content -Path $tempHook -Value $hookContent -Encoding ascii -NoNewline
    Invoke-CheckedCommand -FilePath "scp" -Args @($tempHook, "${HpHost}:~/repos/get_xmltvlisting.git/hooks/post-receive")
    Remove-Item $tempHook -Force -ErrorAction SilentlyContinue
    Invoke-CheckedCommand -FilePath "ssh" -Args @($HpHost, "chmod +x '$HpHookScript' ~/repos/get_xmltvlisting.git/hooks/post-receive")
}

if (-not $SkipGitHub) {
    Write-Host "Pushing to GitHub remote '$GitHubRemote'"
    Invoke-Git -Args @("push", $GitHubRemote, $Branch)
}

if (-not $SkipHp920) {
    Write-Host "Pushing to HP920 remote '$HpRemote'"
    Invoke-Git -Args @("push", $HpRemote, $Branch)
}

Write-Host ""
Write-Host "Expected URLs after publish:"
Write-Host "GitHub folder: https://github.com/AJPnKW/get_xmltvlisting/tree/main/IPTV"
Write-Host "HP920 LAN root: http://192.168.1.73:8011/iptv-epg/"
Write-Host "HP920 reference page: http://192.168.1.73:8011/iptv-epg/IPTV_EPG_Reference.html"
