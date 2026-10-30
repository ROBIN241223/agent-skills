<#
.SYNOPSIS
    Snapshot VinaCAD: process, windows, modal dialogs and the log tail.

.DESCRIPTION
    The fastest way to find out why keystrokes are not landing: a modal dialog
    (class #32770) disables the main window and swallows input. This script lists
    the process, every visible top-level window of that process with its
    enabled/disabled state, the child controls of any #32770 dialog, and the last
    lines of %APPDATA%\VinaCAD\Log.txt.

.PARAMETER ProcessName
    Process name pattern. Default: 'VinaCAD*'.

.PARAMETER LogLines
    How many log lines to show. Default: 15.

.PARAMETER LogPath
    Default: "$env:APPDATA\VinaCAD\Log.txt".

.EXAMPLE
    pwsh -File vcad-status.ps1
    pwsh -File vcad-status.ps1 -LogLines 40
#>
[CmdletBinding()]
param(
    [string]$ProcessName = 'VinaCAD*',
    [int]$LogLines = 15,
    [string]$LogPath = (Join-Path $env:APPDATA 'VinaCAD\Log.txt')
)

if (-not ('Win32Status' -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class Win32Status {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();

    public static uint PID;
    public static List<string> Top() {
        var r = new List<string>();
        EnumWindows((h, l) => {
            uint p; GetWindowThreadProcessId(h, out p);
            if (p == PID && IsWindowVisible(h)) {
                var c = new StringBuilder(128); GetClassName(h, c, 128);
                var t = new StringBuilder(256); GetWindowText(h, t, 256);
                r.Add(h + " [" + c + "] " + (IsWindowEnabled(h) ? "en" : "DIS") + " " + t);
            }
            return true;
        }, IntPtr.Zero);
        return r;
    }
    public static List<string> Kids(IntPtr h) {
        var r = new List<string>();
        EnumChildWindows(h, (k, l) => {
            var c = new StringBuilder(128); GetClassName(k, c, 128);
            var t = new StringBuilder(512); GetWindowText(k, t, 512);
            if (t.Length > 0) r.Add("    " + k + " [" + c + "] " + t);
            return true;
        }, IntPtr.Zero);
        return r;
    }
}
"@
}

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc) { Write-Output "VinaCAD is not running."; exit 0 }

[Win32Status]::PID = $proc.Id
Write-Output ("process   : {0}  pid={1}" -f $proc.ProcessName, $proc.Id)
Write-Output ("main win  : hwnd={0}" -f $proc.MainWindowHandle)
Write-Output ("title     : {0}" -f $proc.MainWindowTitle)
Write-Output ("foreground: hwnd={0}" -f [Win32Status]::GetForegroundWindow())

$top = [Win32Status]::Top()
Write-Output "windows   :"
$top | ForEach-Object { Write-Output ("    " + $_) }

foreach ($w in ($top | Where-Object { $_ -match '\[#32770\]' })) {
    $dh = [IntPtr][int64](($w -split ' ')[0])
    Write-Output ("dialog {0} controls:" -f $dh)
    [Win32Status]::Kids($dh) | ForEach-Object { Write-Output $_ }
}

if (Test-Path $LogPath) {
    Write-Output ("log tail  : {0}" -f $LogPath)
    Get-Content $LogPath -Tail $LogLines | Where-Object {
        $_ -notmatch 'IsVinaCADLicenseValid|OfflineSession|WriteOnlineLog'
    } | ForEach-Object { Write-Output ("    " + $_) }
}
