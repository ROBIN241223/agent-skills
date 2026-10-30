#!/usr/bin/env python3
"""Extract readable content from documents into Markdown.

Handles images (OCR), PDF, Word (.docx/.doc), Excel (.xlsx/.xls), PowerPoint
(.pptx/.ppt), and plain/structured text (txt, md, csv, tsv, json, xml, html, rtf,
odt, ods, odp). Legacy formats are converted with LibreOffice when available.

Usage:
    python extract_document.py FILE [--out OUT.md] [--pages 1-5] [--max-rows 200]
                                   [--max-cols 40] [--no-ocr]

Prints Markdown to stdout; --out also writes it to a file. Non-zero exit on failure
(bad path / unsupported type), but individual sections degrade gracefully.

Design notes:
  * Prefer real libraries (pdfplumber, python-docx, openpyxl, python-pptx, xlrd).
  * Fall back to LibreOffice headless for legacy formats and as a last resort.
  * OCR order: pytesseract (if the tesseract binary exists) -> Windows OCR
    (scripts/win_ocr.ps1) -> a note that the host model can view the image.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # make Vietnamese / any UTF-8 survive on a cp1252 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".ico"}
TEXT_EXTS = {".txt", ".md", ".markdown", ".log", ".rst", ".ini", ".cfg", ".yaml", ".yml"}
HTML_EXTS = {".html", ".htm", ".xml"}
CSV_EXTS = {".csv", ".tsv"}
LEGACY_MAP = {".doc": "docx", ".odt": "docx", ".xls": "xlsx", ".ods": "xlsx",
              ".ppt": "pptx", ".odp": "pptx", ".rtf": "txt"}


# --------------------------------------------------------------------------- utils

def hr(title: str) -> str:
    return f"\n## {title}\n"


def as_cell(v) -> str:
    if v is None:
        return ""
    s = str(v).replace("\r", " ").replace("\n", "<br>")
    return s.replace("|", "\\|").strip()


def md_table(rows, max_rows: int = 200, max_cols: int | None = None) -> str:
    rows = [list(r) for r in rows if r is not None]
    if not rows:
        return ""
    if max_cols:
        rows = [r[:max_cols] for r in rows]
    width = max((len(r) for r in rows), default=0)
    rows = [r + [""] * (width - len(r)) for r in rows]

    def line(cells):
        return "| " + " | ".join(as_cell(c) for c in cells) + " |"

    out = [line(rows[0]), "| " + " | ".join("---" for _ in range(width)) + " |"]
    for r in rows[1:max_rows + 1]:
        out.append(line(r))
    if len(rows) > max_rows + 1:
        out.append(f"\n_(+{len(rows) - max_rows - 1} more rows)_")
    return "\n".join(out)


def soffice() -> str | None:
    for c in ("soffice", "soffice.exe"):
        p = shutil.which(c)
        if p:
            return p
    for c in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice",
              "/usr/bin/soffice", "/usr/local/bin/soffice"):
        if os.path.exists(c):
            return c
    return None


def libreoffice_convert(src: Path, target_ext: str) -> Path | None:
    exe = soffice()
    if not exe:
        return None
    outdir = Path(tempfile.mkdtemp(prefix="docextract_"))
    try:
        subprocess.run([exe, "--headless", "--norestore", "--convert-to", target_ext,
                        "--outdir", str(outdir), str(src)],
                       capture_output=True, timeout=180, check=False)
    except Exception:
        return None
    hits = list(outdir.glob(f"*.{target_ext}"))
    return hits[0] if hits else None


# --------------------------------------------------------------------------- OCR

def ocr_image(path: Path, lang: str = "eng") -> str | None:
    try:
        import pytesseract
        from PIL import Image
        if shutil.which("tesseract"):
            txt = pytesseract.image_to_string(Image.open(path), lang=lang)
            if txt.strip():
                return txt
    except Exception:
        pass
    ps = HERE / "win_ocr.ps1"
    if os.name == "nt" and ps.exists():
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-File", str(ps), "-Path", str(path)],
                               capture_output=True, text=True, encoding="utf-8", timeout=180)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout
        except Exception:
            pass
    return None


# --------------------------------------------------------------------------- extractors

def extract_image(path: Path, do_ocr: bool) -> str:
    out = [hr(f"Image: {path.name}")]
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        im = Image.open(path)
        out.append(f"- format: {im.format}  size: {im.width}x{im.height}  mode: {im.mode}")
        exif = getattr(im, "_getexif", lambda: None)()
        if exif:
            keep = {TAGS.get(k, k): v for k, v in exif.items()
                    if TAGS.get(k, k) in ("Make", "Model", "DateTime", "Orientation", "Software")}
            if keep:
                out.append("- exif: " + json.dumps(keep, default=str))
    except Exception as e:
        out.append(f"- (metadata unavailable: {e})")
    if do_ocr:
        txt = ocr_image(path)
        out.append(hr("OCR text") if txt else "\n_(no OCR backend produced text; the "
                     "host model can view this image directly)_")
        if txt:
            out.append(txt.strip())
    return "\n".join(out)


def extract_pdf(path: Path, pages: set[int] | None, max_rows: int, max_cols: int) -> str:
    out = [hr(f"PDF: {path.name}")]
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            out.append(f"- pages: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages):
                if pages is not None and (i + 1) not in pages:
                    continue
                out.append(hr(f"Page {i + 1}"))
                text = (page.extract_text() or "").strip()
                if text:
                    out.append(text)
                for tbl in page.extract_tables() or []:
                    md = md_table(tbl, max_rows, max_cols)
                    if md:
                        out.append("\n**Table**\n\n" + md)
        return "\n".join(out)
    except Exception as e:
        out.append(f"_pdfplumber failed ({e}); trying pypdf_")
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path))
        for i, page in enumerate(r.pages):
            if pages is not None and (i + 1) not in pages:
                continue
            out.append(hr(f"Page {i + 1}"))
            out.append(page.extract_text() or "_(no text layer)_")
    except Exception as e:
        out.append(f"_pypdf failed too ({e})_")
    return "\n".join(out)


def extract_docx(path: Path, max_rows: int, max_cols: int) -> str:
    out = [hr(f"Word: {path.name}")]
    try:
        import docx
        d = docx.Document(str(path))
        try:
            items = list(d.iter_inner_content())
        except Exception:
            items = list(d.paragraphs)
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        for it in items:
            if isinstance(it, Paragraph):
                t = it.text.strip()
                if t:
                    style = (it.style.name or "") if it.style else ""
                    if style.lower().startswith("heading"):
                        lvl = "".join(ch for ch in style if ch.isdigit()) or "2"
                        out.append("#" * int(lvl) + " " + t)
                    else:
                        out.append(t)
            elif isinstance(it, Table):
                rows = [[c.text for c in row.cells] for row in it.rows]
                md = md_table(rows, max_rows, max_cols)
                if md:
                    out.append("\n" + md)
        return "\n".join(out)
    except Exception as e:
        out.append(f"_python-docx failed ({e}); reading raw XML_")
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        root = ET.fromstring(xml)
        paras = []
        for p in root.iter(f"{ns}p"):
            paras.append("".join(t.text or "" for t in p.iter(f"{ns}t")))
        out.append("\n".join(x for x in paras if x.strip()))
    except Exception as e:
        out.append(f"_raw XML fallback failed too ({e})_")
    return "\n".join(out)


def extract_xlsx(path: Path, max_rows: int, max_cols: int) -> str:
    out = [hr(f"Excel: {path.name}")]
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        for ws in wb.worksheets:
            out.append(hr(f"Sheet: {ws.title}"))
            md = md_table(ws.iter_rows(values_only=True), max_rows, max_cols)
            out.append(md if md else "_(empty)_")
        wb.close()
        return "\n".join(out)
    except Exception as e:
        out.append(f"_openpyxl failed ({e}); trying LibreOffice_")
    conv = libreoffice_convert(path, "csv")
    if conv:
        out.append(hr("Converted by LibreOffice"))
        out.append(conv.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(out)


def extract_xls(path: Path, max_rows: int, max_cols: int) -> str:
    out = [hr(f"Excel (legacy): {path.name}")]
    try:
        import xlrd
        book = xlrd.open_workbook(str(path))
        for sh in book.sheets():
            out.append(hr(f"Sheet: {sh.name}"))
            rows = [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]
            out.append(md_table(rows, max_rows, max_cols) or "_(empty)_")
        return "\n".join(out)
    except Exception as e:
        out.append(f"_xlrd failed ({e}); trying LibreOffice_")
    conv = libreoffice_convert(path, "csv")
    if conv:
        out.append(hr("Converted by LibreOffice"))
        out.append(conv.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(out)


def extract_pptx(path: Path, max_rows: int, max_cols: int) -> str:
    out = [hr(f"PowerPoint: {path.name}")]
    try:
        from pptx import Presentation
        prs = Presentation(str(path))
        for i, slide in enumerate(prs.slides):
            out.append(hr(f"Slide {i + 1}"))
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame.text.strip():
                    out.append(shape.text_frame.text.strip())
                if getattr(shape, "has_table", False) and shape.has_table:
                    rows = [[c.text for c in row.cells] for row in shape.table.rows]
                    out.append("\n" + md_table(rows, max_rows, max_cols))
        return "\n".join(out)
    except Exception as e:
        out.append(f"_python-pptx failed ({e}); trying LibreOffice_")
    conv = libreoffice_convert(path, "txt")
    if conv:
        out.append(hr("Converted by LibreOffice"))
        out.append(conv.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(out)


def extract_csv(path: Path, max_rows: int, max_cols: int) -> str:
    sep = "\t" if path.suffix.lower() == ".tsv" else ","
    out = [hr(f"Table: {path.name}")]
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            sample = f.read(8192)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                sep = dialect.delimiter
            except Exception:
                pass
            rows = list(csv.reader(f, delimiter=sep))
        rows = [r for r in rows if any((c or "").strip() for c in r)]  # drop stray blank rows
        out.append(md_table(rows, max_rows, max_cols))
    except Exception as e:
        out.append(f"_(csv parse failed: {e})_")
    return "\n".join(out)


def extract_text(path: Path) -> str:
    out = [hr(f"Text: {path.name}")]
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            raw = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except Exception:
            pass
    out.append(raw)
    return "\n".join(out)


def extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
        text = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        import html as _html
        text = _html.unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return hr(f"HTML: {path.name}") + "\n" + text.strip()
    except Exception as e:
        return hr(f"HTML: {path.name}") + f"\n_(extract failed: {e})_\n\n" + raw[:5000]


# --------------------------------------------------------------------------- dispatch

def extract(path: Path, args) -> str:
    ext = path.suffix.lower()
    pages = None
    if args.pages:
        pages = set()
        for part in args.pages.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                pages.update(range(int(a), int(b) + 1))
            elif part:
                pages.add(int(part))

    if ext in IMAGE_EXTS:
        return extract_image(path, not args.no_ocr)
    if ext == ".pdf":
        return extract_pdf(path, pages, args.max_rows, args.max_cols)
    if ext == ".docx":
        return extract_docx(path, args.max_rows, args.max_cols)
    if ext == ".xlsx":
        return extract_xlsx(path, args.max_rows, args.max_cols)
    if ext == ".xls":
        return extract_xls(path, args.max_rows, args.max_cols)
    if ext == ".pptx":
        return extract_pptx(path, args.max_rows, args.max_cols)
    if ext in CSV_EXTS:
        return extract_csv(path, args.max_rows, args.max_cols)
    if ext in TEXT_EXTS:
        return extract_text(path)
    if ext in HTML_EXTS:
        return extract_html(path)
    if ext in LEGACY_MAP:
        conv = libreoffice_convert(path, LEGACY_MAP[ext])
        if not conv:
            return f"# {path.name}\n\n_No LibreOffice available to convert {ext}; install LibreOffice._"
        return f"_({ext} converted via LibreOffice -> {conv.suffix})_\n" + extract(conv, args)
    # last resort: sniff
    head = path.read_bytes()[:5]
    if head[:4] == b"%PDF":
        return extract_pdf(path, pages, args.max_rows, args.max_cols)
    if head[:2] == b"PK":
        return (f"# {path.name}\n\n_Unknown OOXML/zip container; "
                "install python-docx / python-pptx / openpyxl for its type._")
    return extract_text(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract document content to Markdown.")
    ap.add_argument("path")
    ap.add_argument("--out", help="also write the Markdown here")
    ap.add_argument("--pages", help="PDF pages, e.g. 1-5 or 1,3,7")
    ap.add_argument("--max-rows", type=int, default=200)
    ap.add_argument("--max-cols", type=int, default=40)
    ap.add_argument("--no-ocr", action="store_true", help="skip OCR for images")
    args = ap.parse_args(argv)

    p = Path(args.path)
    if not p.exists():
        print(f"error: no such file: {p}", file=sys.stderr)
        return 2
    try:
        md = extract(p, args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(md)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"\n_(written to {args.out})_", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
