---
name: Read documents (images, PDF, Word, Excel)
description: >-
  Read the contents of a document and turn it into text or Markdown - images (OCR),
  PDF, Word (.docx/.doc), Excel (.xlsx/.xls), PowerPoint, and CSV/TSV/text/HTML/JSON.
  Extracts text, tables, and metadata. Use when the user provides or points to a
  picture, screenshot, scan, PDF, Word document, spreadsheet, or slide deck and wants
  it read, transcribed, summarized, translated, converted, extracted (tables/data), or
  searched. Vietnamese phrasings - "doc file nay", "doc anh", "doc PDF", "doc Word",
  "doc Excel", "trich xuat noi dung", "chuyen thanh van ban".
---

# Read documents

Turn any common document into text / Markdown that you can then reason about. One
script dispatches by file type so you do not have to remember which library reads
what.

This skill covers **images, PDF, Word, Excel, PowerPoint and text**. For reading then
*researching* a topic from a source with citations, use `$doc-research`; this skill is
the extraction half.

## When to use

- The user attaches or points to a file and asks what it says, what is in it, to
  transcribe it, extract a table, translate it, or summarize it.
- You need to read a `.pdf`, `.docx`, `.xlsx`, `.pptx`, an image/screenshot/scan, or a
  `.csv` before doing something with its content.
- You have data trapped in a spreadsheet and need it as Markdown/CSV.

## Quick start

```bash
python scripts/extract_document.py "C:\path\file.pdf"
python scripts/extract_document.py report.docx --out report.md
python scripts/extract_document.py data.xlsx --max-rows 500
python scripts/extract_document.py scan.jpg            # OCR
python scripts/extract_document.py book.pdf --pages 1-10
```

Output is Markdown on stdout; `--out` additionally writes it to a file. Exit code is
non-zero only if the path is missing or the format is truly unsupported — sections
degrade gracefully and say what failed.

## Supported formats

| Type | Extensions | Library / method |
| --- | --- | --- |
| Images | png, jpg/jpeg, gif, bmp, tif/tiff, webp | Pillow metadata + OCR |
| PDF | pdf | `pdfplumber` (text + tables), fallback `pypdf` |
| Word | docx | `python-docx` (paragraphs + tables, in order) |
| Word (legacy) | doc, odt, rtf | LibreOffice headless convert |
| Excel | xlsx | `openpyxl` (per sheet, Markdown table) |
| Excel (legacy) | xls | `xlrd`, fallback LibreOffice |
| PowerPoint | pptx | `python-pptx` (text frames + tables) |
| PowerPoint (legacy) | ppt, odp | LibreOffice convert |
| Text | txt, md, log, ini, cfg, yaml | direct read |
| Data | csv, tsv, json | `csv` / `json` |
| Markup | html, htm, xml | tag stripping |

## Images and OCR

`extract_document.py` on an image reports dimensions/EXIF and then tries, in order:

1. **`pytesseract`** — only if the `tesseract` binary exists on PATH (not installed by
   default here).
2. **Windows OCR** — `scripts/win_ocr.ps1` uses the built-in `Windows.Media.Ocr`
   engine. Works with no extra install; needs the OCR language pack (English ships
   with Windows; add others under Settings -> Language). Pass `-Language vi-VN` for
   Vietnamese.
3. Otherwise it says so — and remember **the host model can often view the image
   directly**, so for a screenshot a direct read may beat OCR. Use OCR when you need
   text you can search or transform, or when the host cannot see images.

## Backends and installing

See `references/backends.md` for the full dependency matrix. Short version:

- Already present on this machine: `pdfplumber`, `pypdf`, `PyMuPDF` (`fitz`),
  `Pillow`, `openpyxl`, `xlrd`, `python-docx`, `python-pptx`.
- LibreOffice (`soffice`) is present at
  `C:\Program Files\LibreOffice\program\soffice.exe`; it is used for legacy `.doc`,
  `.xls`, `.ppt`, `.odt`, `.ods`, `.odp`, `.rtf`.
- Optional: `pip install pytesseract` **and** install the Tesseract binary for better
  OCR; otherwise rely on `win_ocr.ps1`.

```bash
# ensure the pure-Python readers exist (idempotent)
python -m pip install python-docx python-pptx openpyxl xlrd pdfplumber pypdf PyMuPDF Pillow
```

## Working with the result

- Large output: write to `--out` and then read/grep that file, instead of dumping it
  all into the reply.
- Spreadsheets: keep `--max-cols` modest so wide sheets stay readable; raise
  `--max-rows` when you must see everything.
- PDFs: some pages are scans with no text layer. If a page comes back empty, consider
  rendering it to an image and OCR-ing (PyMuPDF can rasterise: `page.get_pixmap()`),
  then run the image through `extract_document.py`.
- Quote and cite the source file and page/sheet/slide when you use its content.

## Files in this skill

- `scripts/extract_document.py` — the dispatcher (all formats).
- `scripts/win_ocr.ps1` — Windows OCR fallback for images.
- `references/backends.md` — dependency matrix and install commands.

## Reporting

Say which file(s) you read, the format, and where the content came from (page / sheet /
slide). If OCR or a conversion was involved, say so and flag any uncertainty in the
text.
