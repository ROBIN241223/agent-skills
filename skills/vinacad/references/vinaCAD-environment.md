# VinaCAD environment notes

Facts learned by probing a VinaCAD Free installation on Windows 11. Paths are
machine-specific — rediscover them if they differ (see "Rediscovering paths").

## Application

| Item | Value (observed) |
| --- | --- |
| Product | Prima VinaCAD 2026.9.4 - VinaCAD Free |
| Main executable | `C:\Users\Lenovo\AppData\Local\Programs\VinaCAD\VinaCAD 2026\VinaCAD.exe` |
| Engine | IntelliCAD / ODA (Teigha); DWG + DXF read/write |
| Roaming config | `C:\Users\Lenovo\AppData\Roaming\VinaCAD\` |
| Log file | `C:\Users\Lenovo\AppData\Roaming\VinaCAD\Log.txt` (UTF-8) |
| Per-version config | `C:\Users\Lenovo\AppData\Roaming\VinaCAD\VinaCAD 2026\` |
| Plugin autoload | `C:\Users\Lenovo\AppData\Roaming\VinaCAD\ApplicationPlugins\` |
| COM type library | `C:\Users\Lenovo\AppData\Local\Programs\VinaCAD\VinaCAD 2026\VinaCadCOM.tlb` |
| Fonts (SHX) | `C:\Users\Lenovo\AppData\Local\Programs\VinaCAD\VinaCAD 2026\Fonts\` |

The exe name is `VinaCAD.exe` (not `VinaCADApp.exe`). The shell file association
opens drawings via the app.

## Command line

- `VinaCAD.exe "<file>"` — open `<file>`. If an instance is already running it is
  forwarded (`/O "<file>"`) to that instance and the new process exits.
- `VinaCAD.exe /O "<file>"` — same, explicit.
- `VinaCAD.exe /b "<script.scr>"` — **parsed** ("Run script file: ...") but the
  script is **not executed** in this build. Do not rely on it.
- `<file> /b <script>` and `/O <file> /b <script>` — **do not combine**; the parser
  stops at the first non-switch (`/O`) argument.
- The app writes license/online checks to the log every few seconds
  (`IsVinaCADLicenseValid`, `[OfflineSession]`) — harmless noise to filter out.

## COM / ActiveX

- `VinaCadCOM.tlb` declares the `VinaCadApplication` coclass:
  CLSID `{F9689BBB-CF53-4704-9F22-076871194D9A}`. The document/server types expose
  methods such as `VcadDocument::SaveAs`.
- The server is **not registered** (`HKCR\CLSID\{F9689BBB-...}` is absent), so
  `CreateObject` / `comtypes.client.CreateObject` fails out of the box.
- Theoretical route: register `HKCU\Software\Classes\CLSID\{F9689BBB-...}\LocalServer32`
  pointing at `VinaCAD.exe /Automation` (or `/Embedding`) and drop the TLB into the
  comtypes cache. This is **unverified** — keystrokes are the reliable path.

## Plugins

- `%APPDATA%\VinaCAD\ApplicationPlugins\<name>.bundle\` using the AutoCAD-style
  `PackageContents.xml` **is parsed** (the runtime matches `Platform="VinaCAD"`), but
  the loader rejects `.lsp` components with **"Unsupported component type"**, so it is
  not a usable scripting backdoor for LISP.

## DWG / backup behaviour

- Saving produces DWG with an `AC10xx` header: `AC1032` = DWG 2018, `AC1027` = 2013,
  `AC1024` = 2010.
- VinaCAD/AutoCAD keep the previous file as a `.bak`. The `.bak` next to the save
  target (and, for cloud-backed documents, `%APPDATA%\VinaCAD\<name>.bak`) can be a
  genuine DWG — inspect the first 6 bytes before discarding it.
- Autosave writes `%APPDATA%\VinaCAD\<name>_<n>_<hash>.sv$`.

## Rediscovering paths

```powershell
Get-Process VinaCAD* | Select-Object Id,MainWindowTitle,Path
Get-Command VinaCAD.exe -ErrorAction SilentlyContinue
Get-ChildItem "$env:LOCALAPPDATA\Programs\VinaCAD" -Recurse -Filter VinaCAD.exe
Get-ChildItem "$env:APPDATA\VinaCAD" -Force
```

## Version note

Everything here was observed on VinaCAD Free 2026.9.4. A future build may register
COM, honour `/b`, or accept LISP plugins; re-probe before assuming the limitations
still hold.
