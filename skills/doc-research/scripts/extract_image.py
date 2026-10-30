#!/usr/bin/env python3
"""Read an image file: metadata, OCR text, and basic info.

Usage:
  python extract_image.py FILE [--meta] [--ocr] [--lang eng] [--out OUT]
  python extract_image.py --clipboard [--meta] [--ocr]

OCR engines:
  --engine auto       try pytesseract (Tesseract) first, then Windows OCR (default)
  --engine tesseract  force Tesseract via pytesseract
  --engine windows    force Windows.Media.Ocr (Windows only, no install needed)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)


def get_meta(path):
    try:
        from PIL import Image, ExifTags
    except Exception as exc:
        return {"error": f"Pillow not installed (pip install pillow): {exc}"}
    try:
        with Image.open(path) as im:
            info = {
                "format": im.format,
                "mode": im.mode,
                "width": im.width,
                "height": im.height,
                "size_bytes": os.path.getsize(path),
            }
            exif = getattr(im, "getexif", lambda: None)()
            if exif:
                tags = {}
                for k, v in exif.items():
                    name = ExifTags.TAGS.get(k, k)
                    tags[str(name)] = str(v)
                info["exif"] = tags
            return info
    except Exception as exc:
        return {"error": f"could not open image: {exc}"}


def ocr_tesseract(path, lang):
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:
        return None, f"pytesseract/Pillow not installed (pip install pytesseract pillow): {exc}"
    try:
        with Image.open(path) as im:
            text = pytesseract.image_to_string(im, lang=lang)
        return text, None
    except Exception as exc:
        return None, f"Tesseract OCR failed (is the tesseract binary installed and on PATH?): {exc}"


def ocr_windows(path, lang):
    """OCR via Windows.Media.Ocr using the bundled PowerShell helper (no install)."""
    if not sys.platform.startswith("win"):
        return None, "Windows OCR is only available on Windows"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "win_ocr.ps1")
    if not os.path.isfile(script):
        return None, f"win_ocr.ps1 not found next to extract_image.py ({script})"
    # Tesseract lang codes are close to BCP-47; take the first (e.g. "eng+vie" -> "en").
    win_lang = ""
    if lang:
        first = lang.split("+")[0].strip()
        mapping = {"eng": "en-US", "vie": "vi-VN"}
        win_lang = mapping.get(first, first)
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", script, "-Path", path,
    ]
    if win_lang:
        cmd += ["-Lang", win_lang]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            return None, f"Windows OCR failed (exit {proc.returncode}): {proc.stderr.strip()}"
        return proc.stdout, None
    except Exception as exc:
        return None, f"Windows OCR failed: {exc}"


def ocr(path, lang, engine):
    errors = []
    if engine in ("auto", "tesseract"):
        text, err = ocr_tesseract(path, lang)
        if err is None:
            return text, "tesseract", None
        errors.append(err)
        if engine == "tesseract":
            return None, None, " | ".join(errors)
    if engine in ("auto", "windows"):
        text, err = ocr_windows(path, lang)
        if err is None:
            return text, "windows", None
        errors.append(err)
    return None, None, " | ".join(errors)


def capture_clipboard():
    """Save the clipboard image to a temp PNG via PowerShell. Returns path or error."""
    if not sys.platform.startswith("win"):
        return None, "clipboard capture is only available on Windows"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "read_clipboard_image.ps1")
    if not os.path.isfile(script):
        return None, f"read_clipboard_image.ps1 not found next to extract_image.py ({script})"
    out = os.path.join(tempfile.gettempdir(), "opencode", "clipboard_read.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", script, "-Out", out, "-Force",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as exc:
        return None, f"clipboard capture failed: {exc}"
    stdout = (proc.stdout or "").strip()
    if stdout.startswith("SAVED:"):
        return stdout[len("SAVED:"):].strip(), None
    return None, stdout or (proc.stderr or "").strip() or "no image on clipboard"


def main():
    ap = argparse.ArgumentParser(description="Read image metadata and optional OCR text.")
    ap.add_argument("path", nargs="?", help="image file path (omit when using --clipboard)")
    ap.add_argument("--clipboard", action="store_true",
                    help="grab the image currently on the Windows clipboard")
    ap.add_argument("--meta", action="store_true", help="print image metadata (default)")
    ap.add_argument("--ocr", action="store_true", help="run OCR and print extracted text")
    ap.add_argument("--lang", default="eng", help="Tesseract languages, e.g. eng+vie")
    ap.add_argument("--engine", default="auto", choices=["auto", "tesseract", "windows"],
                    help="OCR engine selection (default: auto)")
    ap.add_argument("--out", help="write output here (default: stdout)")
    args = ap.parse_args()

    path = args.path
    if args.clipboard:
        if path and os.path.isfile(path):
            eprint(f"[extract_image] --clipboard given; ignoring path {path!r}")
        path, err = capture_clipboard()
        if err:
            eprint(f"[extract_image] {err}")
            return 3
        eprint(f"[extract_image] captured clipboard image -> {path}")
    if not path:
        eprint("[extract_image] no input: pass a FILE or --clipboard")
        return 2
    if not os.path.isfile(path):
        eprint(f"[extract_image] file not found: {path}")
        return 2

    buf = []
    if args.meta or not args.ocr:
        buf.append("== METADATA ==")
        buf.append(json.dumps(get_meta(path), indent=2, ensure_ascii=False))

    if args.ocr:
        text, used, err = ocr(path, args.lang, args.engine)
        if err:
            buf.append("\n== OCR ==\n" + err)
            eprint("[extract_image] " + err)
            eprint("[extract_image] Tip: use the host vision/read tool to read the image directly.")
        else:
            buf.append(f"\n== OCR (engine: {used}, lang: {args.lang}) ==\n{text or '(no text detected)'}")

    out = "\n".join(buf)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        eprint(f"[extract_image] wrote {len(out)} chars to {args.out}")
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
