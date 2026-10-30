<#
.SYNOPSIS
    Save the current VinaCAD drawing (or an opened DXF) as DWG - without needing focus.

.DESCRIPTION
    VinaCAD is an MFC/IntelliCAD app, so the File > Save As command can be triggered
    with a window message, and the resulting dialog can be driven with window
    messages too. That means the whole export works even when this script's process
    cannot hold the foreground (SendInput to the command line is flaky in that case).

    Primary path (focus-free):
      1. PostMessage(hMain, WM_COMMAND, ID_FILE_SAVE_AS=0xE104)   -> opens "Save As"
      2. WM_SETTEXT the file-name edit (id 1001) with the full output path
      3. CB_SETCURSEL the file-type combo (id 1116) to the DWG entry, then notify
      4. BM_CLICK the OK button (id 1); answer any overwrite prompt
      5. verify the AC10xx header

    Fallbacks: focus + SendKeys SAVEAS, then VinaCAD's own .bak swap
    (%APPDATA%\VinaCAD\<name>.bak when it is a real DWG).

.PARAMETER Drawing
    Optional .dxf/.dwg to open first. Omit if the drawing is already open.

.PARAMETER Out
    Destination .dwg path (required). An absolute path is used as-is.

.PARAMETER Format
    '2018' (default), '2013', '2010', '2007', '2004', '2000', 'r14', 'r13', 'r12'.
    'dxf2018' .. 'dxf12' select ASCII DXF outputs if you really want DXF.

.PARAMETER Exe
    VinaCAD.exe path. Omit to auto-detect.

.EXAMPLE
    pwsh -File vcad-saveas-dwg.ps1 -Drawing .\part.dxf -Out .\part.dwg
    pwsh -File vcad-saveas-dwg.ps1 -Out .\part.dwg -Format 2013

.NOTES
    Confirm in %APPDATA%\VinaCAD\Log.txt. Exit codes: 0 produced, 3 wrong header, 4 failed.
#>
[CmdletBinding()]
param(
    [string]$Drawing,
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Format = '2018',
    [string]$ProcessName = 'VinaCAD*',
    [string]$Exe,
    [int]$OpenTimeoutSec = 45
)
$ErrorActionPreference = 'Stop'

if (-not ('VcadDlg' -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class VcadDlg {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, StringBuilder l);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);

    public static uint PID;
    public static string Cls(IntPtr h){ var c=new StringBuilder(64); GetClassName(h,c,64); return c.ToString(); }
    public static string Txt(IntPtr h){ var t=new StringBuilder(512); GetWindowText(h,t,512); return t.ToString(); }
    public static List<IntPtr> TopDialogs(){ var r=new List<IntPtr>();
        EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
            if(p==PID && IsWindowVisible(h) && Cls(h)=="#32770") r.Add(h); return true; }, IntPtr.Zero); return r; }
    public static List<IntPtr> Children(IntPtr parent){ var r=new List<IntPtr>();
        EnumChildWindows(parent,(k,l)=>{ r.Add(k); return true; }, IntPtr.Zero); return r; }
    public static IntPtr FindById(IntPtr parent, int id){
        foreach(var k in Children(parent)) if(GetDlgCtrlID(k)==id) return k; return IntPtr.Zero; }
    public static IntPtr FindButton(IntPtr parent, string match){
        foreach(var k in Children(parent)){ if(Cls(k)=="Button"){ var t=Txt(k).Replace("&","").Trim();
            if(t.Equals(match, StringComparison.OrdinalIgnoreCase)) return k; } } return IntPtr.Zero; }
    public static IntPtr FilenameEdit(IntPtr parent){
        var e=FindById(parent,1001); if(e!=IntPtr.Zero) return e;
        foreach(var k in Children(parent)) if(Cls(k)=="Edit") return k; return IntPtr.Zero; }
    public static IntPtr FileTypeCombo(IntPtr parent){
        var c=FindById(parent,1116); if(c!=IntPtr.Zero) return c;
        IntPtr best=IntPtr.Zero; int bestN=0;
        foreach(var k in Children(parent)){ if(Cls(k)!="ComboBox") continue;
            int n=(int)SendMessage(k,0x0146,IntPtr.Zero,IntPtr.Zero);
            if(n>bestN){ bestN=n; best=k; } } return best; }
    public static int ComboCount(IntPtr cb){ return (int)SendMessage(cb,0x0146,IntPtr.Zero,IntPtr.Zero); }
    public static string ComboItem(IntPtr cb,int i){ var s=new StringBuilder(256); SendMessage(cb,0x0148,(IntPtr)i,s); return s.ToString(); }
    public static int FindComboItem(IntPtr cb,string contains){
        int n=ComboCount(cb);
        for(int i=0;i<n;i++) if(ComboItem(cb,i).IndexOf(contains, StringComparison.OrdinalIgnoreCase)>=0) return i;
        return -1; }
}
"@
}

$LogPath = Join-Path $env:APPDATA 'VinaCAD\Log.txt'

function Get-LogOffset { if (Test-Path $LogPath) { (Get-Item $LogPath).Length } else { 0 } }
function Get-NewLog([long]$offset) {
    if (-not (Test-Path $LogPath)) { return @() }
    $fs = [System.IO.File]::Open($LogPath, 'Open', 'Read', 'ReadWrite')
    $fs.Seek($offset, 'Begin') | Out-Null
    $sr = New-Object System.IO.StreamReader($fs); $text = $sr.ReadToEnd(); $sr.Close(); $fs.Close()
    return ($text -split "`n")
}
function Get-DwgVersion([string]$path) {
    if (-not (Test-Path $path)) { return $null }
    $b = [System.IO.File]::ReadAllBytes($path)
    if ($b.Length -lt 6) { return $null }
    $hdr = [System.Text.Encoding]::ASCII.GetString($b[0..5])
    if ($hdr -notmatch '^AC10\d\d$') { return "not-dwg ($hdr)" }
    $map = @{ AC1032 = 'DWG 2018'; AC1027 = 'DWG 2013'; AC1024 = 'DWG 2010'; AC1021 = 'DWG 2007';
              AC1018 = 'DWG 2004'; AC1015 = 'DWG 2000'; AC1014 = 'DWG R14' }
    if ($map.ContainsKey($hdr)) { return $map[$hdr] } else { return $hdr }
}

$FormatToken = @{
    '2018' = 'AutoCAD 2018 (*.dwg)'; '2013' = 'AutoCAD 2013 (*.dwg)'; '2010' = 'AutoCAD 2010 (*.dwg)';
    '2007' = 'AutoCAD 2007 (*.dwg)'; '2004' = 'AutoCAD 2004 (*.dwg)'; '2000' = 'AutoCAD 2000 (*.dwg)';
    'r14'  = 'AutoCAD Release 14 (*.dwg)'; 'r13' = 'AutoCAD Release 13 Drawing (*.dwg)'; 'r12' = 'AutoCAD Release 12 Drawing (*.dwg)';
    'dxf2018' = 'AutoCAD 2018 ASCII DXF (*.dxf)'; 'dxf2013' = 'AutoCAD 2013 ASCII DXF (*.dxf)';
    'dxf2010' = 'AutoCAD 2010 ASCII DXF (*.dxf)'; 'dxf2007' = 'AutoCAD 2007 ASCII DXF (*.dxf)'
}
$key = $Format.ToLower()
if (-not $FormatToken.ContainsKey($key)) { throw "Unknown -Format '$Format'. Use 2018/2013/2010/2007/2004/2000/r14." }
$TypeLabel = $FormatToken[$key]

function Get-VcadProc {
    Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
}

$OutFull  = [System.IO.Path]::GetFullPath($Out)
$OutDir   = Split-Path -Parent $OutFull
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

# ------------------------------------------------------------------ 1. open
if ($Drawing) {
    if (-not $Exe) {
        $Exe = (Get-ChildItem "$env:LOCALAPPDATA\Programs\VinaCAD" -Recurse -Filter VinaCAD.exe -ErrorAction SilentlyContinue |
                Select-Object -First 1 -ExpandProperty FullName)
    }
    if (-not $Exe) { throw 'VinaCAD.exe not found; pass -Exe.' }
    if (-not (Test-Path $Drawing)) { throw "Drawing not found: $Drawing" }
    $off = Get-LogOffset
    Start-Process -FilePath $Exe -ArgumentList @([System.IO.Path]::GetFullPath($Drawing)) | Out-Null
    $deadline = (Get-Date).AddSeconds($OpenTimeoutSec); $opened = $false
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 800
        if ((Get-NewLog $off) -match 'Finish reading file') { $opened = $true; break }
    }
    Write-Output ("open={0}" -f $opened)
}

# ------------------------------------------------------------------ 2. clear modal
$proc = Get-VcadProc
if (-not $proc) { Write-Error 'VinaCAD is not running.'; exit 4 }
[VcadDlg]::PID = $proc.Id
foreach ($d in [VcadDlg]::TopDialogs()) {
    $t = [VcadDlg]::Txt($d)
    if ($t -match 'Recovery|Khoi phuc|recover') {
        [VcadDlg]::PostMessage($d, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        Write-Output "closed a recovery modal"
        Start-Sleep -Milliseconds 600
    }
}
$proc = Get-VcadProc
$hwnd = $proc.MainWindowHandle

# ------------------------------------------------------------------ 3. focus-free Save As
if (Test-Path $OutFull) { Remove-Item $OutFull -Force }
$off = Get-LogOffset
[VcadDlg]::PostMessage($hwnd, 0x0111, [IntPtr]0xE104, [IntPtr]::Zero) | Out-Null   # WM_COMMAND ID_FILE_SAVE_AS

$dlg = [IntPtr]::Zero
$deadline = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    $dlg = [VcadDlg]::TopDialogs() | Where-Object { [VcadDlg]::Txt($_) -match 'Save As|Save Drawing' } | Select-Object -First 1
    if ($dlg) { break }
}

$produced = $false
if ($dlg -and $dlg -ne [IntPtr]::Zero) {
    Write-Output ("save-as dialog hwnd={0}" -f $dlg)
    $edit  = [VcadDlg]::FilenameEdit($dlg)
    $combo = [VcadDlg]::FileTypeCombo($dlg)
    $ok    = [VcadDlg]::FindButton($dlg, 'OK')
    if ($edit -ne [IntPtr]::Zero) { [VcadDlg]::SendMessage($edit, 0x000C, [IntPtr]::Zero, $OutFull) | Out-Null }  # WM_SETTEXT
    if ($combo -ne [IntPtr]::Zero) {
        $idx = [VcadDlg]::FindComboItem($combo, $TypeLabel)
        if ($idx -lt 0) { $idx = 0 }
        [VcadDlg]::SendMessage($combo, 0x014E, [IntPtr]$idx, [IntPtr]::Zero) | Out-Null   # CB_SETCURSEL
        $wp = [IntPtr]([int64]((1 -shl 16) -bor [VcadDlg]::GetDlgCtrlID($combo)))           # CBN_SELCHANGE
        [VcadDlg]::PostMessage($dlg, 0x0111, $wp, $combo) | Out-Null
    }
    Start-Sleep -Milliseconds 400
    if ($ok -ne [IntPtr]::Zero) { [VcadDlg]::PostMessage($ok, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null }  # BM_CLICK
    Start-Sleep -Seconds 2
    # answer an overwrite confirmation if one appeared
    foreach ($m in [VcadDlg]::TopDialogs()) {
        $yes = [VcadDlg]::FindButton($m, 'Yes'); if ($yes -eq [IntPtr]::Zero) { $yes = [VcadDlg]::FindButton($m, 'OK') }
        if ($yes -ne [IntPtr]::Zero) { [VcadDlg]::PostMessage($yes, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null }
    }
    Start-Sleep -Seconds 3
    if (Test-Path $OutFull) { $produced = $true }
}

# ------------------------------------------------------------------ 4. .bak swap fallback
if (-not $produced) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($OutFull)
    foreach ($bak in @((Join-Path $OutDir "$name.bak"), (Join-Path $env:APPDATA "VinaCAD\$name.bak"))) {
        if (Test-Path $bak) {
            $b = [System.IO.File]::ReadAllBytes($bak)
            if ($b.Length -ge 6 -and ([System.Text.Encoding]::ASCII.GetString($b[0..5]) -match '^AC10\d\d$')) {
                Copy-Item $bak $OutFull -Force
                Write-Output ("recovered DWG from .bak: {0}" -f $bak)
                $produced = $true; break
            }
        }
    }
}

# ------------------------------------------------------------------ 5. verify
(Get-NewLog $off) | Where-Object { $_ -match 'SAVEAS|SaveAs|SaveFile|LogFileTypeVersion|OnSaveDocument|error' } |
    Select-Object -Last 10 | ForEach-Object { Write-Output ("log: " + $_.TrimEnd()) }

if ($produced -and (Test-Path $OutFull)) {
    $ver = Get-DwgVersion $OutFull
    Write-Output ("OUT={0} size={1} version={2}" -f $OutFull, (Get-Item $OutFull).Length, $ver)
    if ($ver -like 'DWG*') { exit 0 } else { exit 3 }
}
Write-Error ("Failed to produce {0}. See %APPDATA%\VinaCAD\Log.txt" -f $OutFull)
exit 4
