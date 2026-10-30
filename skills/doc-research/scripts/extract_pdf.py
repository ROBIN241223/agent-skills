#!/usr/bin/env python3
"""Extract text, tables, metadata, and page images from a PDF.

Gracefully picks the best available backend and prints which one it used.
Backend order: pdfplumber -> pymupdf -> pypdf -> pdftotext(CLI) -> minimal builtin.

Usage:
  python extract_pdf.py FILE [--mode text|tables|meta|all|render]
                             [--pages 1-5,10] [--out OUT]
                             [--ocr] [--lang eng] [--render-dir DIR] [--dpi 200]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import zlib

def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)

# ---------------------------------------------------------------- page ranges
def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            a = int(a) if a else 1
            b = int(b) if b else n
            out.extend(range(a - 1, min(b, n)))
        else:
            out.append(int(part) - 1)
    seen, res = set(), []
    for p in out:
        if 0 <= p < n and p not in seen:
            seen.add(p)
            res.append(p)
    return res

# ---------------------------------------------------------------- backends
def _has(mod):
    import importlib.util
    return importlib.util.find_spec(mod) is not None

def _mupdf():
    """Return the PyMuPDF module, preferring the modern `pymupdf` name."""
    try:
        import pymupdf as m
        return m
    except Exception:
        import fitz as m
        return m

def pdfplumber_text(path, pages):
    import pdfplumber
    chunks = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        sel = pages if pages else range(total)
        for i in sel:
            t = pdf.pages[i].extract_text() or ""
            chunks.append((i + 1, t))
    return chunks

def pdfplumber_tables(path, pages):
    import pdfplumber
    result = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        sel = pages if pages else range(total)
        for i in sel:
            for j, table in enumerate(pdf.pages[i].extract_tables() or []):
                result.append((i + 1, j + 1, table))
    return result

def fitz_text(path, pages):
    fitz = _mupdf()
    doc = fitz.open(path)
    total = doc.page_count
    sel = pages if pages else range(total)
    return [(i + 1, doc.load_page(i).get_text("text") or "") for i in sel]

def pypdf_text(path, pages):
    from pypdf import PdfReader
    reader = PdfReader(path)
    total = len(reader.pages)
    sel = pages if pages else range(total)
    return [(i + 1, reader.pages[i].extract_text() or "") for i in sel]

def pdftotext_cli(path, pages):
    exe = _which("pdftotext")
    if not exe:
        raise FileNotFoundError("pdftotext not found")
    cmd = [exe, "-layout"]
    if pages and len(pages) >= 1:
        cmd += ["-f", str(min(pages) + 1), "-l", str(max(pages) + 1)]
    cmd += [path, "-"]
    out = subprocess.run(cmd, capture_output=True, timeout=300)
    text = out.stdout.decode("utf-8", "replace")
    parts = text.split("\f")
    if not pages:
        pages = list(range(len(parts)))
    return [(pages[k] + 1, parts[k]) for k in range(len(parts)) if parts[k].strip()]

def _which(name):
    from shutil import which
    return which(name)

# ---------------------------------------------------------------- fallback
def minimal_text(path, pages):
    """Best-effort text from uncompressed / FlateDecode content streams. No deps."""
    data = open(path, "rb").read()
    texts = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = m.group(1)
        try:
            raw = zlib.decompress(raw)
        except Exception:
            pass
        if b"BT" not in raw and b"Tj" not in raw and b"TJ" not in raw:
            continue
        chunk = []
        for tm in re.finditer(rb"\((?:\\.|[^\\()])*\)", raw):
            s = tm.group(0)[1:-1]
            s = s.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
            chunk.append(s.decode("latin-1", "replace"))
        if chunk:
            texts.append(" ".join(chunk))
    joined = "\n".join(texts)
    return [(1, joined)]  # cannot reliably map to pages

def extract_text(path, pages):
    # returns (chunks, backend_name, total_hint)
    for name, fn in (("pdfplumber", pdfplumber_text),
                     ("pymupdf", fitz_text),
                     ("pypdf", pypdf_text),
                     ("pdftotext", pdftotext_cli)):
        try:
            chunks = fn(path, pages)
            if chunks:
                return chunks, name
        except Exception as exc:  # backend missing or failed
            eprint(f"[extract_pdf] backend {name} unavailable/failed: {exc}")
    eprint("[extract_pdf] Falling back to minimal builtin parser (low fidelity).")
    eprint("[extract_pdf] Install for better results: pip install pdfplumber pymupdf pypdf")
    return minimal_text(path, pages), "minimal-builtin"

# ---------------------------------------------------------------- metadata
def get_meta(path):
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        info = dict(r.metadata or {})
        info["pages"] = len(r.pages)
        return info
    except Exception:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            info = dict(pdf.metadata or {})
            info["pages"] = len(pdf.pages)
            return info
    except Exception:
        pass
    try:
        fitz = _mupdf()
        doc = fitz.open(path)
        info = dict(doc.metadata or {})
        info["pages"] = doc.page_count
        return info
    except Exception:
        pass
    return {"pages": "unknown", "note": "no metadata backend available"}

# ---------------------------------------------------------------- OCR / render
def render_pages(path, pages, out_dir, dpi, fmt="png"):
    fitz = _mupdf()
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(path)
    total = doc.page_count
    sel = pages if pages else range(total)
    written = []
    for i in sel:
        pix = doc.load_page(i).get_pixmap(dpi=dpi)
        fp = os.path.join(out_dir, f"page-{i + 1:03d}.{fmt}")
        pix.save(fp)
        written.append(fp)
    return written

def ocr_pdf(path, pages, lang):
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(f"OCR needs pytesseract + Pillow: pip install pytesseract pillow ({exc})")
    fitz = _mupdf()
    doc = fitz.open(path)
    total = doc.page_count
    sel = pages if pages else range(total)
    chunks = []
    for i in sel:
        pix = doc.load_page(i).get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        chunks.append((i + 1, pytesseract.image_to_string(img, lang=lang)))
    return chunks

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Extract text/tables/metadata from a PDF.")
    ap.add_argument("path")
    ap.add_argument("--mode", choices=["text", "tables", "meta", "all", "render"], default="text")
    ap.add_argument("--pages", help="e.g. 1-5,10 (1-based)")
    ap.add_argument("--out", help="write output here (default: stdout)")
    ap.add_argument("--ocr", action="store_true", help="OCR scanned pages instead of text layer")
    ap.add_argument("--lang", default="eng", help="Tesseract languages, e.g. eng+vie")
    ap.add_argument("--render-dir", default="pdf-pages", help="dir for --mode render")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        eprint(f"[extract_pdf] file not found: {args.path}")
        return 2

    # page count hint (best effort)
    total = None
    try:
        m = get_meta(args.path)
        if isinstance(m.get("pages"), int):
            total = m["pages"]
    except Exception:
        pass
    pages = parse_pages(args.pages, total) if total else None

    buf = []
    if args.mode in ("meta", "all"):
        buf.append("== METADATA ==")
        buf.append(json.dumps(get_meta(args.path), indent=2, default=str, ensure_ascii=False))
        buf.append("")

    if args.mode == "render":
        try:
            files = render_pages(args.path, pages, args.render_dir, args.dpi)
            for f in files:
                print(f)
            eprint(f"[extract_pdf] rendered {len(files)} page(s) to {args.render_dir}/")
            return 0
        except Exception as exc:
            eprint(f"[extract_pdf] render failed: {exc}")
            return 1

    if args.mode in ("text", "all"):
        if args.ocr:
            try:
                chunks = ocr_pdf(args.path, pages, args.lang)
                backend = f"ocr(pytesseract:{args.lang})"
            except Exception as exc:
                eprint(f"[extract_pdf] OCR failed: {exc}")
                chunks, backend = extract_text(args.path, pages)
        else:
            chunks, backend = extract_text(args.path, pages)
        buf.append(f"== TEXT (backend: {backend}) ==")
        for pno, text in chunks:
            buf.append(f"\n----- page {pno} -----\n{text}")

    if args.mode in ("tables", "all"):
        try:
            tables = pdfplumber_tables(args.path, pages)
            buf.append("\n== TABLES ==")
            for pno, tno, table in tables:
                buf.append(f"\n--- page {pno} table {tno} ---")
                sio = io.StringIO()
                csv.writer(sio).writerows(table)
                buf.append(sio.getvalue())
        except Exception as exc:
            buf.append(f"\n== TABLES ==\n(not available: {exc}; install: pip install pdfplumber)")

    out = "\n".join(buf)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        eprint(f"[extract_pdf] wrote {len(out)} chars to {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
