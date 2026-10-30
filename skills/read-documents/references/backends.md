# Backends and dependencies

Which library reads which format, what is already installed on this machine, and how
to add what is missing.

## Dependency matrix

| Format | Primary backend | Fallback |
| --- | --- | --- |
| pdf (text + tables) | `pdfplumber` | `pypdf` (text only), LibreOffice, PyMuPDF rasterise + OCR |
| docx | `python-docx` | unzip `word/document.xml` |
| doc, odt, rtf | LibreOffice `--convert-to docx`/`txt` | — |
| xlsx | `openpyxl` | LibreOffice `--convert-to csv` |
| xls | `xlrd` | LibreOffice `--convert-to csv` |
| pptx | `python-pptx` | LibreOffice `--convert-to txt` |
| ppt, odp | LibreOffice | — |
| csv/tsv | stdlib `csv` | — |
| json | stdlib `json` | — |
| html/xml | regex tag stripping | — |
| images | `Pillow` (metadata) + OCR | — |
| image OCR | `pytesseract` (needs Tesseract binary) | Windows OCR (`win_ocr.ps1`) |

## Status on this machine

Installed for the interpreter `python`
(`C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe`, 3.12):

- `pdfplumber`, `pypdf`, `PyMuPDF` (`fitz`), `Pillow`, `openpyxl`, `xlrd`,
  `python-docx`, `python-pptx`.
- LibreOffice at `C:\Program Files\LibreOffice\program\soffice.exe`.
- NOT installed: the `tesseract` binary (so `pytesseract` cannot be used yet — image
  OCR falls back to Windows OCR).

Add the pure-Python readers (idempotent):

```bash
python -m pip install python-docx python-pptx openpyxl xlrd pdfplumber pypdf PyMuPDF Pillow
```

## Enabling better OCR (optional)

1. Install Tesseract (e.g. the UB-Mannheim build on Windows), put `tesseract.exe` on
   PATH, then `python -m pip install pytesseract`.
2. Check languages: `tesseract --list-langs`. Vietnamese is `vie`; the script defaults
   to `eng` and accepts `-Language`/`lang` where wired up.

Without Tesseract, `win_ocr.ps1` uses Windows.Media.Ocr: reliable for clean printed
text, and needs the relevant language pack for non-English.

## LibreOffice conversion

`extract_document.py` calls:

```bash
soffice --headless --norestore --convert-to <ext> --outdir <tmp> <file>
```

It writes into a temp dir and reads the first matching output. If `soffice` is already
running interactively the headless conversion can fail; close the GUI or retry.

## Rasterising scanned PDF pages

When a PDF page has no text layer, render it and OCR the image:

```python
import pymupdf  # or: import fitz
doc = pymupdf.open("scan.pdf")
page = doc[0]
page.get_pixmap(dpi=300).save("page1.png")
```

Then run `extract_document.py page1.png`.
