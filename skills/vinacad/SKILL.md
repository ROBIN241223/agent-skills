---
name: VinaCAD automation & DWG export
description: >-
  Drive VinaCAD (Prima VinaCAD, an IntelliCAD/AutoCAD-compatible CAD app on Windows)
  from an agent - open DXF/DWG drawings, run command-line commands by keystrokes,
  dismiss the "Drawing Recovery" modal, force its window to the foreground, and save
  or export a drawing as .dwg. Use whenever a task involves VinaCAD, Prima VinaCAD,
  IntelliCAD, exporting or saving a drawing as DWG, scripting the VinaCAD command
  line, the Drawing Recovery dialog, or automating a Windows CAD GUI. Vietnamese
  phrasings - "tu dong hoa VinaCAD", "gui lenh bang phim", "xuat .dwg",
  "xu ly hop thoai khoi phuc ban ve".
---

# VinaCAD automation (Windows)

VinaCAD is a Vietnamese AutoCAD/IntelliCAD-compatible CAD application. This skill
captures the non-obvious parts of automating it: opening a drawing, driving its
commands and dialogs with no human at the keyboard, getting past its modal dialogs,
and producing a real `.dwg`.

**Golden rule: verify every step in `%APPDATA%\VinaCAD\Log.txt`.** The app traces
commands, prompts and file I/O there. It is your only reliable feedback channel when
driving the GUI — never assume a keystroke "worked".

Related skills: build the 2D geometry with `$dxf` (build123d) or `$cad`, and enrich a
drawing (frame, title block, spec table) with `ezdxf`. This skill is the VinaCAD
application layer and the DXF -> DWG step.

## When to use

- The user says "open it in VinaCAD", "mo cho tao VinaCAD", "luu thanh DWG", or wants a
  drawing delivered to VinaCAD.
- You must convert a `.dxf` to `.dwg` and VinaCAD is the only CAD app available.
- You need to run VinaCAD commands (OPEN, SAVEAS, ZOOM, SCRIPT) without a person
  clicking.
- A VinaCAD window is stuck behind a modal dialog, or keystrokes are not landing.

## Preferred method: drive VinaCAD with window messages (no focus needed)

**Do not rely on the keyboard.** VinaCAD is an MFC application, so commands and
dialogs can be driven entirely with window messages, which works even while your
process is in the background and cannot hold the foreground.

- **Trigger a command by its MFC command ID.** Post a `WM_COMMAND` to the main frame:

  ```powershell
  PostMessage($hMain, 0x0111, [IntPtr]0xE104, [IntPtr]::Zero)   # ID_FILE_SAVE_AS
  ```

  `0xE100` = File New, `0xE101` = File Open, `0xE103` = File Save, `0xE104` = File
  Save As (standard MFC ids). `0xE104` opens the "Save As" dialog even from the
  background.

- **Drive the dialog with messages.** For the "Save As" dialog the control ids are
  fixed (see the table below): `WM_SETTEXT` the file-name edit, `CB_SETCURSEL` the
  file-type combo, `BM_CLICK` the OK button. No keystrokes, deterministic.

`scripts/vcad-saveas-dwg.ps1` implements this exact sequence. It was verified to
produce a valid `AC1032` (DWG 2018) file with the editor in the background and exit
code 0.

Verified facts that make this work:

| Thing | Value |
| --- | --- |
| Main frame class | `Afx:...` (MFC), e.g. titled `Prima VinaCAD 2026.9.4 - ...` |
| `WM_COMMAND` | `0x0111`; `wParam` = command id (low word) |
| `ID_FILE_SAVE_AS` | `0xE104` → opens `#32770` titled `Save As` |
| Save-As file-name edit | control id `1001` (an `Edit` inside combo `1115`) |
| Save-As file-type combo | control id `1116`, item `0` = `AutoCAD 2018 (*.dwg)` |
| Save-As OK button | control id `1` |

To set the file-type combo, also notify the dialog of the change:
`PostMessage($dlg, 0x0111, MAKEWPARAM(1116, CBN_SELCHANGE=1), $combo)`.

## Opening a drawing

Launch the exe with the file as an argument. A running instance receives it via
`/O "<file>"` and opens it there; otherwise a new process starts:

```powershell
& "C:\Users\Lenovo\AppData\Local\Programs\VinaCAD\VinaCAD 2026\VinaCAD.exe" "C:\path\drawing.dxf"
# or reuse a running instance:
Start-Process -FilePath $exe -ArgumentList @($file)
```

Verify in the log: `CVinaCADApp::openFile [Finish reading file: NAME]`.

## Workflow: DXF -> DWG

```powershell
# 0. (optional) clear a stale crash flag / close a blocking recovery modal
pwsh -File scripts\vcad-dismiss-recovery.ps1

# 1. open the drawing (launches or forwards to the running instance)
Start-Process -FilePath $exe -ArgumentList @('C:\path\drawing.dxf')

# 2. save as DWG - focus-free, message-driven
pwsh -File scripts\vcad-saveas-dwg.ps1 -Drawing 'C:\path\drawing.dxf' -Out 'C:\path\drawing.dwg'

# 3. verify: the first 6 bytes are "AC1032" (DWG 2018) etc.
```

`vcad-saveas-dwg.ps1` posts `0xE104`, fills the dialog, clicks OK, answers an
overwrite prompt, and finally falls back to VinaCAD's own `.bak` swap if needed. The
result is verified by header.

### If the expected file is missing, check the `.bak`

VinaCAD/AutoCAD keep the previous version as a `.bak`, and for cloud-backed documents
the local cache is `%APPDATA%\VinaCAD\<name>.bak`. That file is often a **real DWG** —
check its first 6 bytes (`AC10xx`); if so, copy it to `<name>.dwg`. The log line
`CVinaCADDoc::LogFileTypeVersion [Original file type: DWG, version: 2018]` confirms the
format that was written. This is how the sample drawing's DWG was recovered.

## The "Save As" dialog in detail

Enumerated on VinaCAD Free 2026.9.4 (a `#32770` titled `Save As`):

| Control | Class | id | Notes |
| --- | --- | --- | --- |
| file name | `Edit` (in combo `1115`) | `1001` | `WM_SETTEXT` an absolute path |
| file type | `ComboBox` | `1116` | 32 items; `[0]`=`AutoCAD 2018 (*.dwg)`, `[1]`=2013, `[2]`=2010, ... |
| OK | `Button` | `1` | `BM_CLICK` (`0x00F5`) |
| Cancel | `Button` | `2` | |
| Help | `Button` | `9` | |
| Cloud storages | `Static` + `Button` | `1243`/`1241` | the dialog can default to cloud storage |
| Local files | `Static` + `Button` | `1242`/`17010` (`Browse...`) | |
| file list | `SysListView32` | `1249` | |

Setting an **absolute** output path in the file-name edit saves to that path even when
the cloud tab is shown (verified).

## Getting past VinaCAD-specific blockers

- **"Drawing Recovery" modal.** After VinaCAD is force-killed it flags the next start
  as a crash and opens a modal (`#32770` titled `VinaCAD Application`) mentioning
  *Drawing Recovery* / *Khoi phuc ban ve*. It disables the main window, so keystrokes
  silently do nothing. Close it with `WM_CLOSE` (`0x0010`) —
  `scripts/vcad-dismiss-recovery.ps1` does this.
- **Prefer a graceful close.** Send `WM_CLOSE` to the main window (or the `QUIT`
  command) instead of `Stop-Process`, otherwise you create the crash flag above.
- **Startup `/b script` is parsed but not executed**, and `<file> /b <script>` does not
  combine (the parser stops at the first non-switch argument). Drive the running
  instance instead.
- **COM/ActiveX is declared but not registered.** `VinaCadCOM.tlb` declares
  `VinaCadApplication` (CLSID `{F9689BBB-CF53-4704-9F22-076871194D9A}`) but there is no
  `HKCR\CLSID` entry, so `CreateObject("VinaCad.Application")` fails. Keystrokes and
  window messages are the practical interface.
- **`%APPDATA%\VinaCAD\ApplicationPlugins\*.bundle` autoloads**, but the loader rejects
  `.lsp` components ("Unsupported component type"), so it is not a scripting backdoor.

## Keyboard fallback (only if messages cannot do the job)

Windows blocks `SetForegroundWindow`, `AppActivate` and `SwitchToThisWindow` from a
background process. The one generic trick is **minimize then restore**
(`ShowWindow(h, 6)` then `ShowWindow(h, 9)`) — `scripts/vcad-focus.ps1`.

Even then it is racy: focus can return to the user's active window between the focus
check and the keystroke, so `WScript.Shell.SendKeys` may land nowhere. `PostMessage`
`WM_CHAR` never reaches the command line. Use `scripts/vcad-send.ps1` only when there
is no command id / dialog, and always confirm via the log.

| Goal | Keys (SendKeys) |
| --- | --- |
| Suppress file dialogs | `FILEDIA` ⏎ then `0` ⏎ |
| Open (dialog suppressed) | `_.OPEN` ⏎ then full path ⏎ |
| Save as DWG | prefer `vcad-saveas-dwg.ps1`; else `SAVEAS` ⏎ and drive the dialog |
| Run a script | `SCRIPT` ⏎ then the `.scr` path ⏎ |
| Close cleanly | `QUIT` ⏎ |

Escape SendKeys metacharacters `( ) { } + ^ % ~`; a bad escape throws *"Value does not
fall within the expected range"* and nothing is sent.

## Reading the log

`%APPDATA%\VinaCAD\Log.txt` (UTF-8). Lines worth grepping:

| Pattern | Meaning |
| --- | --- |
| `CVinaCADApp::openFile [Finish reading file: NAME]` | the drawing opened |
| `CVinaCADDoc::ExecuteCommand [ExecuteCommand name: [CMD]...]` | a command started |
| `CVinaCADDoc::getString [Prompt [...]]` | the app is waiting for a typed answer |
| `CmdReactor::commandEnded [cmdName: CMD]` | the command finished |
| `CVinaCADDoc::LogFileTypeVersion [Original file type: DWG, version: ...]` | format written |
| `CMainFrame::OnClose [_____CLOSE APP_____]` | a graceful exit |
| `IsVinaCADLicenseValid`, `[OfflineSession]`, `WriteOnlineLog` | license noise — ignore |

## Files in this skill

- `scripts/vcad-saveas-dwg.ps1` — **DXF/DWG -> DWG, focus-free** (window messages).
- `scripts/vcad-focus.ps1` — bring the window to the foreground (minimize/restore).
- `scripts/vcad-send.ps1` — focus, then send keystrokes (fallback).
- `scripts/vcad-dismiss-recovery.ps1` — close the Drawing Recovery modal.
- `scripts/vcad-status.ps1` — process/window/dialog/log snapshot.
- `references/vinaCAD-environment.md` — paths, versions, argv, COM, log.
- `references/windows-gui-automation.md` — the generic Windows techniques.
- `references/spur-gear-dxf-recipe.md` — worked example (80-tooth gear -> DXF sheet -> DWG).
- `scripts/gear_80T.py`, `scripts/build_gear_sheet.py` — the worked example's sources.

## Reporting

State the output path, its byte size, and the DWG version you verified (e.g.
"`AC1032` = DWG 2018, reopened in VinaCAD"). If a step only partially worked, say which
one and what the log showed.
