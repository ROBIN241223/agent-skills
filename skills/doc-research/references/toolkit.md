# Toolkit — libraries, CLIs, and install matrix

All scripts in `scripts/` degrade gracefully: they detect which backend is present
and print an install hint when one is missing. No dependency is mandatory, but
quality and coverage improve a lot with the optional ones installed.

## Python packages

| Task | Preferred | Alternatives | Install |
| --- | --- | --- | --- |
| PDF text (layout-aware) | `pdfplumber` | `pypdf`, `pymupdf` (fitz) | `pip install pdfplumber` |
| PDF text (fast/simple) | `pypdf` | `PyPDF2` | `pip install pypdf` |
| PDF text + render pages | `pymupdf` (fitz) | `pdf2image` (+poppler) | `pip install pymupdf` |
| PDF tables | `pdfplumber` | `camelot-py`, `tabula` | `pip install pdfplumber` |
| Image open / metadata | `Pillow` (PIL) | — | `pip install pillow` |
| OCR (images + scans) | `pytesseract` + Tesseract | `easyocr`, `paddleocr` | `pip install pytesseract` |
| Render PDF pages to images | `pymupdf` | `pdf2image` (+poppler) | `pip install pymupdf` |
| Office docs → text (optional) | `markitdown` | `python-docx`, `openpyxl` | `pip install "markitdown[all]"` |
| HTML → text (research) | stdlib `html.parser` | `beautifulsoup4`, `trafilatura` | `pip install beautifulsoup4 trafilatura` |

Recommended one-liner:

```bash
pip install pdfplumber pypdf pymupdf pillow pytesseract
```

## External CLIs (optional, faster on big files)

| Tool | Purpose | Notes |
| --- | --- | --- |
| `pdftotext` | PDF → text | Poppler. `pdftotext -layout in.pdf out.txt` |
| `pdftoppm` | PDF → PNG/JPG pages | Poppler. `pdftoppm -r 200 -png in.pdf page` |
| `pdfimages` | Extract embedded images | Poppler. `pdfimages -j in.pdf img` |
| `tesseract` | OCR engine | `tesseract img.png out -l eng+vie` |
| `qpdf` | Merge/split/decrypt PDFs | `qpdf --decrypt in.pdf out.pdf` |
| `magick` (ImageMagick) | Image convert/resize | `magick in.heic out.png` |

Windows installs: Tesseract and Poppler are separate binaries (add them to `PATH`).
If a CLI is missing, the scripts fall back to the Python backends.

## OCR language packs

`--lang` takes Tesseract language codes. Mixtures use `+` (e.g. `eng+vie`).
Common ones: `eng`, `vie`, `chi_sim`, `jpn`, `kor`, `fra`, `deu`, `spa`.

Check installed packs with: `tesseract --list-langs`.

## Which backend does the script pick?

`extract_pdf.py` tries, in order: `pdfplumber` → `pymupdf` → `pypdf` → `pdftotext`
→ a minimal built-in parser (uncompressed/Flate text streams only). The chosen
backend is printed to stderr so you know how trustworthy the output is.

`extract_image.py` uses `Pillow` for metadata and `pytesseract` for OCR. Without
`pytesseract`, it still reports image metadata and tells you to use the host vision
tool for content.
