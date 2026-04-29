<#
.SYNOPSIS
    Manual one-shot launcher: runs the capstone pipeline once inside WSL.

.DESCRIPTION
    Useful for ad-hoc runs without going through Task Scheduler.
    Streams output live in the current PowerShell window AND writes a
    timestamped log to C:\pipeline-logs\.

.PARAMETER Distro
    WSL distro name. Default: Ubuntu.

.PARAMETER WslUser
    Linux user to run as. Default: rjg.

.PARAMETER ExtraArgs
    Optional extra args forwarded to scripts/run-pipeline.sh, e.g. --days 7

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\Run-Pipeline.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\Run-Pipeline.ps1 -ExtraArgs '--days 7'
#>

[CmdletBinding()]
param(
    [string] $Distro   = 'Ubuntu',
    [string] $WslUser  = 'rjg',
    [string] $ExtraArgs = ''
)

$ErrorActionPreference = 'Stop'

$wslExe = Join-Path $env:WINDIR 'System32\wsl.exe'
if (-not (Test-Path $wslExe)) { throw "wsl.exe not found at $wslExe" }

$winLogDir = 'C:\pipeline-logs'
if (-not (Test-Path $winLogDir)) { New-Item -ItemType Directory -Path $winLogDir | Out-Null }

$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$logPath   = Join-Path $winLogDir "pipeline_manual_${timestamp}.log"

$wslWrapper = "/home/$WslUser/coding/capstone/scripts/run-pipeline-auto.sh"
$bashCmd    = "$wslWrapper $ExtraArgs"

Write-Host "Launching pipeline inside WSL ($Distro as $WslUser)..." -ForegroundColor Cyan
Write-Host "Command: wsl.exe -d $Distro -u $WslUser -- bash -lc `"$bashCmd`""
Write-Host "Log:     $logPath"
Write-Host ''

& $wslExe -d $Distro -u $WslUser -- bash -lc "$bashCmd" 2>&1 | Tee-Object -FilePath $logPath
$exit = $LASTEXITCODE

Write-Host ''
if ($exit -eq 0) {
    Write-Host "Pipeline finished successfully." -ForegroundColor Green
} else {
    Write-Host "Pipeline exited with code $exit." -ForegroundColor Red
}
exit $exit
