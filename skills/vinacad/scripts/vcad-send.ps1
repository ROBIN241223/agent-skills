<#
.SYNOPSIS
    Bring VinaCAD to the foreground and send keystrokes to its command line.

.DESCRIPTION
    VinaCAD's command line needs REAL keyboard input: PostMessage WM_CHAR to the
    frame window does not reach it, but WScript.Shell.SendKeys does - once the app
    is the foreground window. This script focuses first (via vcad-focus.ps1) and
    then sends each payload in order with a delay.

.PARAMETER Keys
    One or more SendKeys payloads, sent in order. Escape metacharacters in the
    payload yourself: ( ) { } + ^ % ~  e.g. '(' -> '{(}'  ')' -> '{)}'.

.PARAMETER DelayMs
    Delay between payloads. Default: 750 ms.

.PARAMETER ProcessName
    Process name pattern. Default: 'VinaCAD*'.

.PARAMETER NoFocus
    Do not focus first (assume VinaCAD is already foreground).

.EXAMPLE
    pwsh -File vcad-send.ps1 -Keys 'FILEDIA{ENTER}','0{ENTER}'
    pwsh -File vcad-send.ps1 -Keys '_.-SAVEAS{ENTER}','2018{ENTER}','C:/out/part.dwg{ENTER}'

.NOTES
    Always confirm the effect in %APPDATA%\VinaCAD\Log.txt.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string[]]$Keys,
    [int]$DelayMs = 750,
    [string]$ProcessName = 'VinaCAD*',
    [switch]$NoFocus
)
$ErrorActionPreference = 'Stop'

if (-not $NoFocus) {
    $report = & "$PSScriptRoot\vcad-focus.ps1" -ProcessName $ProcessName
    if ($report -notmatch 'focus=True') {
        throw "Could not bring VinaCAD to the foreground: $report"
    }
}

$wsh = New-Object -ComObject WScript.Shell
foreach ($k in $Keys) {
    $wsh.SendKeys($k)
    Start-Sleep -Milliseconds $DelayMs
}
Write-Output ("sent {0} payload(s)" -f $Keys.Count)
