<#
.SYNOPSIS
    Close the VinaCAD "Drawing Recovery" modal (and other #32770 blockers).

.DESCRIPTION
    After VinaCAD is force-killed it flags the next launch as a crash and opens a
    modal dialog (class #32770, title "VinaCAD Application") mentioning Drawing
    Recovery / "Khoi phuc ban ve". The modal disables the main window, so keystrokes
    silently do nothing. This script finds such dialogs in the VinaCAD process and
    sends WM_CLOSE (0x0010), which dismisses a message box without clicking OK.

    By default only dialogs whose text/title looks like a recovery prompt are
    closed. Use -Any to close any #32770 dialog owned by VinaCAD.

.PARAMETER ProcessName
    Process name pattern. Default: 'VinaCAD*'.

.PARAMETER Any
    Close every #32770 dialog owned by the process, not just recovery prompts.

.EXAMPLE
    pwsh -File vcad-dismiss-recovery.ps1
#>
[CmdletBinding()]
param(
    [string]$ProcessName = 'VinaCAD*',
    [switch]$Any
)

if (-not ('Win32Dismiss' -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class Win32Dismiss {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);

    public static uint PID;
    public static List<IntPtr> Dialogs() {
        var r = new List<IntPtr>();
        EnumWindows((h, l) => {
            uint p; GetWindowThreadProcessId(h, out p);
            var c = new StringBuilder(64); GetClassName(h, c, 64);
            if (p == PID && IsWindowVisible(h) && c.ToString() == "#32770") r.Add(h);
            return true;
        }, IntPtr.Zero);
        return r;
    }
    public static string Text(IntPtr h) {
        var t = new StringBuilder(2048); GetWindowText(h, t, 2048);
        EnumChildWindows(h, (k, l) => {
            var u = new StringBuilder(2048); GetWindowText(k, u, 2048);
            if (u.Length > 0) t.Append(' ').Append(u);
            return true;
        }, IntPtr.Zero);
        return t.ToString();
    }
}
"@
}

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc) { Write-Output "VinaCAD is not running."; exit 0 }
[Win32Dismiss]::PID = $proc.Id

$closed = 0
foreach ($d in [Win32Dismiss]::Dialogs()) {
    $text = [Win32Dismiss]::Text($d)
    $isRecovery = $text -match 'Recovery|Khoi phuc|Kh\x00f4i ph\x1ee5c|recover'
    if ($Any -or $isRecovery) {
        [Win32Dismiss]::PostMessage($d, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        $closed++
        Write-Output ("closed dialog {0}: {1}" -f $d, ($text.Substring(0, [Math]::Min(120, $text.Length))))
    }
    else {
        Write-Output ("left dialog {0} (not a recovery prompt; use -Any to close): {1}" -f $d, ($text.Substring(0, [Math]::Min(120, $text.Length))))
    }
}
if ($closed -eq 0) { Write-Output "No blocking dialog found." }
