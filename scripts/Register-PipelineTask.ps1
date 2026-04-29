<#
.SYNOPSIS
    Registers a Windows Task Scheduler job that runs the capstone pipeline
    inside WSL every 6 hours.

.DESCRIPTION
    The task invokes `wsl.exe -d Ubuntu -u rjg bash -lc "<repo>/scripts/run-pipeline-auto.sh"`,
    which activates the project's venv, runs phases 1-4 locally (so the
    YouTube scraper uses your home IP rather than the IP-banned server),
    then triggers phases 5-7 on the production API.

    Logs land in BOTH locations:
        WSL:     ~/coding/capstone/logs/pipeline_<timestamp>.log
        Windows: C:\pipeline-logs\pipeline_<timestamp>.log

    The script self-elevates to Administrator (required by Task Scheduler).

.PARAMETER IntervalHours
    How often the task should run. Default: 6.

.PARAMETER StartTime
    First fire time (any later runs repeat at IntervalHours).
    Defaults to the next aligned 6-hour boundary (00:00, 06:00, 12:00, 18:00).

.PARAMETER Distro
    WSL distro name. Default: Ubuntu.

.PARAMETER WslUser
    Linux user to run the script as. Default: rjg.

.PARAMETER TaskName
    Scheduled-task name. Default: CapstonePipelineAuto.

.PARAMETER RunNow
    Trigger an immediate run after registering, useful for verifying.

.PARAMETER Unregister
    Remove the scheduled task and exit.

.EXAMPLE
    # Standard install (will prompt for UAC elevation)
    powershell -ExecutionPolicy Bypass -File .\scripts\Register-PipelineTask.ps1

.EXAMPLE
    # Install + run once immediately
    powershell -ExecutionPolicy Bypass -File .\scripts\Register-PipelineTask.ps1 -RunNow

.EXAMPLE
    # Remove the task
    powershell -ExecutionPolicy Bypass -File .\scripts\Register-PipelineTask.ps1 -Unregister
#>

[CmdletBinding()]
param(
    [int]    $IntervalHours = 6,
    [datetime] $StartTime,
    [string] $Distro    = 'Ubuntu',
    [string] $WslUser   = 'rjg',
    [string] $TaskName  = 'CapstonePipelineAuto',
    [switch] $RunNow,
    [switch] $Unregister
)

$ErrorActionPreference = 'Stop'

# ---- Self-elevate to Administrator -----------------------------------------
$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Host 'Re-launching elevated (UAC prompt incoming)...' -ForegroundColor Yellow
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
    foreach ($kv in $PSBoundParameters.GetEnumerator()) {
        if ($kv.Value -is [switch]) {
            if ($kv.Value.IsPresent) { $argList += "-$($kv.Key)" }
        } else {
            $argList += "-$($kv.Key)"
            $argList += "`"$($kv.Value)`""
        }
    }
    Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -Verb RunAs
    return
}

# ---- Unregister path -------------------------------------------------------
if ($Unregister) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'." -ForegroundColor Green
    } else {
        Write-Host "No task named '$TaskName' is registered." -ForegroundColor Yellow
    }
    return
}

# ---- Ensure WSL is available ----------------------------------------------
$wslExe = Join-Path $env:WINDIR 'System32\wsl.exe'
if (-not (Test-Path $wslExe)) {
    throw "wsl.exe not found at $wslExe. Is WSL installed?"
}

$installedDistros = & $wslExe --list --quiet 2>$null |
    ForEach-Object { $_ -replace "`0", '' } |
    Where-Object { $_ -and $_.Trim() } |
    ForEach-Object { $_.Trim() }
if ($installedDistros -notcontains $Distro) {
    Write-Warning "Distro '$Distro' was not found by 'wsl --list'. Detected: $($installedDistros -join ', ')"
}

# ---- Make sure the Windows log directory exists ----------------------------
$winLogDir = 'C:\pipeline-logs'
if (-not (Test-Path $winLogDir)) {
    New-Item -ItemType Directory -Path $winLogDir | Out-Null
    Write-Host "Created $winLogDir" -ForegroundColor Green
}

# ---- Make sure the bash wrapper exists -------------------------------------
$wslWrapper = "/home/$WslUser/coding/capstone/scripts/run-pipeline-auto.sh"
$wrapperCheck = & $wslExe -d $Distro -u $WslUser -- bash -lc "test -x '$wslWrapper' && echo OK || echo MISSING"
$wrapperCheck = ($wrapperCheck | Out-String).Trim()
if ($wrapperCheck -ne 'OK') {
    Write-Warning "$wslWrapper is not executable inside WSL."
    Write-Host  "Run inside WSL:  chmod +x $wslWrapper" -ForegroundColor Yellow
}

# ---- Build the scheduled-task action --------------------------------------
$bashCmd = "$wslWrapper >> /home/$WslUser/coding/capstone/logs/cron.log 2>&1"
$action  = New-ScheduledTaskAction `
    -Execute $wslExe `
    -Argument "-d $Distro -u $WslUser -- bash -lc `"$bashCmd`""

# ---- Trigger: first run at next aligned IntervalHours boundary -------------
if (-not $StartTime) {
    $now    = Get-Date
    $hour   = [Math]::Ceiling($now.Hour / [double]$IntervalHours) * $IntervalHours
    $base   = $now.Date.AddHours($hour)
    if ($base -le $now) { $base = $base.AddHours($IntervalHours) }
    $StartTime = $base
}

$trigger = New-ScheduledTaskTrigger -Once -At $StartTime `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)

# Run only when the user is logged on (WSL needs a user session). Use the
# current interactive user so mounted /mnt/c paths and ssh-agent etc. work.
$currentUser = "$env:USERDOMAIN\$env:USERNAME"
$principalArgs = @{
    UserId    = $currentUser
    LogonType = 'Interactive'
    RunLevel  = 'Highest'
}
$taskPrincipal = New-ScheduledTaskPrincipal @principalArgs

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

# ---- Register (replacing any prior copy) ----------------------------------
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Replaced existing task '$TaskName'." -ForegroundColor Yellow
}

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $action `
    -Trigger   $trigger `
    -Principal $taskPrincipal `
    -Settings  $settings `
    -Description "Runs the capstone YouTube pipeline inside WSL ($Distro) every $IntervalHours hours from your home IP." | Out-Null

Write-Host ''
Write-Host "Registered '$TaskName'." -ForegroundColor Green
Write-Host "  First run : $StartTime"
Write-Host "  Repeat    : every $IntervalHours hours"
Write-Host "  Runs as   : $currentUser (interactive logon)"
Write-Host "  Command   : wsl.exe -d $Distro -u $WslUser -- bash -lc `"$bashCmd`""
Write-Host "  Logs      : C:\pipeline-logs\  and  \\wsl.localhost\$Distro\home\$WslUser\coding\capstone\logs\"
Write-Host ''

if ($RunNow) {
    Write-Host 'Starting an immediate run for verification...' -ForegroundColor Cyan
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
    Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo |
        Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime
    Write-Host "Tail the live log with:" -ForegroundColor Cyan
    Write-Host "  Get-Content -Wait (Get-ChildItem C:\pipeline-logs\pipeline_*.log | Sort LastWriteTime | Select -Last 1).FullName"
}
