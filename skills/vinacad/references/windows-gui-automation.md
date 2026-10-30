# Windows GUI automation for CAD apps

Techniques for driving a stubborn Windows desktop app (VinaCAD, but the same applies
to AutoCAD/IntelliCAD/BricsCAD) when the usual automation hooks are unavailable.
The agent runs as a background process, so **focus and modal dialogs are the two
things that break everything else**.

## 0. Prefer window messages over keystrokes (no focus needed)

Keystrokes need the foreground; window messages do not. For MFC/IntelliCAD/AutoCAD
apps, both **commands** and **dialogs** can be driven by messages, which is far more
reliable than fighting for focus:

- **Commands.** The main frame handles menu/accelerator commands as
  `WM_COMMAND` (`0x0111`) with `wParam` = the command id (low word). MFC uses standard
  ids: `ID_FILE_NEW=0xE100`, `ID_FILE_OPEN=0xE101`, `ID_FILE_SAVE=0xE103`,
  `ID_FILE_SAVE_AS=0xE104`. So `PostMessage(hMain, 0x0111, 0xE104, 0)` opens
  *File > Save As* even from a background process.

- **Dialogs.** Enumerate the dialog's children and act by control:

  | Action | Message |
  | --- | --- |
  | set a text field | `WM_SETTEXT` (`0x000C`) on the `Edit` |
  | choose a combo item | `CB_SETCURSEL` (`0x014E`), then `WM_COMMAND(MAKEWPARAM(id, CBN_SELCHANGE=1), hCombo)` to the dialog |
  | read combo item | `CB_GETCOUNT` (`0x0146`) / `CB_GETLBTEXT` (`0x0148`) |
  | press a button | `BM_CLICK` (`0x00F5`) on the `Button` |
  | close a message box | `WM_CLOSE` (`0x0010`) on the dialog |

  Identify controls by `GetClassName` and `GetDlgCtrlID` — record the ids once, they
  are stable for a given app version.

This is how `vcad-saveas-dwg.ps1` produces a DWG with the editor in the background.

## 1. Windows will not let a background process steal focus

`SetForegroundWindow`, `WScript.Shell.AppActivate` and the undocumented
`SwitchToThisWindow` all fail when the caller is not already foreground and did not
receive the last input event. `AttachThreadInput` to the foreground thread usually
fails too.

The trick that works: **minimize then restore the target window.**

```powershell
[Win]::ShowWindow($h, 6)   # SW_MINIMIZE
[Win]::ShowWindow($h, 9)   # SW_RESTORE
# now GetForegroundWindow() == $h
```

Always confirm with `GetForegroundWindow()` before sending input, and never send
keystrokes unless the target is foreground — otherwise they land in whatever window
*is* focused (e.g. the user's chat console).

## 2. Keystrokes need real input, and the right app

- `WScript.Shell.SendKeys` (via `SendInput`) works once the window is foreground.
- `PostMessage WM_CHAR` / `WM_KEYDOWN` to the frame window does **not** reach the
  command line of these apps. Do not bother.
- Getting text reliably: split the work — send the command token, `{ENTER}`, then
  arguments, `{ENTER}`. Add small sleeps (400-900 ms) between steps.
- Escape SendKeys metacharacters in the payload: `(` -> `{(}`, `)` -> `{)}`,
  `{` -> `{{`, `}` -> `}}`, plus `+ ^ % ~`. A bad escape throws
  *"Value does not fall within the expected range"* and the string is not sent.

## 3. Enumerate windows to find the real blocker

A disabled main window (`IsWindowEnabled` == false) means a **modal dialog** owns the
input. Standard dialogs use class `#32770`. Find them and read their child static
texts:

```powershell
# top-level windows of a PID: class + title + enabled/disabled
# child controls of a dialog: class + text  -> read the message, find buttons
```

`scripts/vcad-status.ps1` does this and also prints the log tail.

## 4. Dismiss a dialog programmatically

- `PostMessage(hDlg, 0x0010, 0, 0)` = `WM_CLOSE` — closes a message box without
  clicking (works when the dialog only offers OK, as with crash-recovery prompts).
- To press a specific button, find the child `Button` whose text matches
  (`OK`, `Yes`, `No`, `Cancel`) and send it `BM_CLICK` (`0x00F5`).
- To fill a text field, `WM_SETTEXT` on the child `Edit`; for a combo, `CB_SETCURSEL`
  then notify the parent with `WM_COMMAND`.

## 5. Prefer a graceful shutdown

Force-killing a CAD app makes it flag the next launch as a crash and open a
recovery modal, which then breaks your keystrokes. Close with `WM_CLOSE` on the main
window or a `QUIT` command.

## 6. Verify through the app's own log, not through pixels

You usually cannot see the screen. Every modern CAD app writes a log (VinaCAD:
`%APPDATA%\VinaCAD\Log.txt`). Read the tail after each action and look for the
command/prompt/file events. "I sent the keys" is not evidence; "the log shows the
command started and ended" is.

## 7. Helper skeleton

The `scripts/*.ps1` files here are small, self-contained and reusable:

- `vcad-focus.ps1` — find process, minimize/restore, confirm foreground.
- `vcad-send.ps1` — focus then `SendKeys` a sequence.
- `vcad-status.ps1` — process/window/modal/log snapshot.
- `vcad-dismiss-recovery.ps1` — `WM_CLOSE` the recovery modal.
- `vcad-saveas-dwg.ps1` — the full save-as-DWG routine.

They embed the P/Invoke surface in a small C# class via `Add-Type`, so they have no
dependencies beyond Windows PowerShell / PowerShell 7.
