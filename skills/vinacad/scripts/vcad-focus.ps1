<#
.SYNOPSIS
    Force the VinaCAD main window to the foreground.

.DESCRIPTION
    Windows blocks SetForegroundWindow / AppActivate / SwitchToThisWindow from a
    process that is not already foreground. The one trick that reliably works from
    a background script is to MINIMIZE the target window and then RESTORE it.
    This script tries the cheap calls first and falls back to minimize/restore,
    confirming with GetForegroundWindow each time.

.PARAMETER ProcessName
    Process name pattern. Default: 'VinaCAD*'.

.PARAMETER TimeoutSeconds
    Keep retrying for this long. Default: 12.

.EXAMPLE
    pwsh -File vcad-focus.ps1
    # focus=True hwnd=1245800 pid=20396 title=Prima VinaCAD 2026.9.4 - VinaCAD Free - ...

.NOTES
    Sends nothing. Safe to run repeatedly. Exit codes: 0 ok, 1 no window, 2 could not focus.
#>
[CmdletBinding()]
param(
    [string]$ProcessName = 'VinaCAD*',
    [int]$TimeoutSeconds = 12
)

if (-not ('Win32Focus' -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class Win32Focus {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool alt);
}
"@
}

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) {
    Write-Error "No windowed process matches '$ProcessName'."
    exit 1
}
$h = $proc.MainWindowHandle
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ok = $false

while ((Get-Date) -lt $deadline) {
    if ([Win32Focus]::GetForegroundWindow() -eq $h) { $ok = $true; break }

    [Win32Focus]::SwitchToThisWindow($h, $true)
    Start-Sleep -Milliseconds 200
    if ([Win32Focus]::GetForegroundWindow() -eq $h) { $ok = $true; break }

    [Win32Focus]::ShowWindow($h, 6) | Out-Null      # SW_MINIMIZE
    Start-Sleep -Milliseconds 400
    [Win32Focus]::ShowWindow($h, 9) | Out-Null      # SW_RESTORE
    Start-Sleep -Milliseconds 600
    if ([Win32Focus]::GetForegroundWindow() -eq $h) { $ok = $true; break }
}

Write-Output ("focus={0} hwnd={1} pid={2} title={3}" -f $ok, $h, $proc.Id, $proc.MainWindowTitle)
if (-not $ok) { exit 2 }
