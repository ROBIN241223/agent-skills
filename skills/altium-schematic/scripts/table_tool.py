#!/usr/bin/env python3
"""Read tabular BOM / netlist exports: .csv, .xls (xlrd), .xlsx (openpyxl or raw).

Handles real supplier exports such as an LCSC "BOM Quotation" .xls, Altium
component-export spreadsheets, and generic CSV BOMs.

Usage:
  python table_tool.py read FILE [--sheet NAME|N] [--list-sheets] [--json] [--out OUT]
  python table_tool.py headers FILE          # just show column headers + row count
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import zipfile

def eprint(*a):
    print(*a, file=sys.stderr)

def detect(path):
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    if head.startswith(b"PK\x03\x04"):
        return "xlsx"
    if head.startswith(b"|RECORD="):
        return "text-records"
    return "csv"

def read_csv(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except Exception:
        dialect = csv.excel
    rows = [list(map(lambda c: c.strip(), row)) for row in csv.reader(io.StringIO(text), dialect)]
    return [("csv", rows)]

def read_xls(path):
    import xlrd
    wb = xlrd.open_workbook(path)
    out = []
    for sh in wb.sheets():
        rows = [[str(sh.cell_value(r, c)) for c in range(sh.ncols)] for r in range(sh.nrows)]
        out.append((sh.name, rows))
    return out

def read_xlsx(path):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            rows = [[("" if c is None else str(c)) for c in row] for row in ws.iter_rows(values_only=True)]
            out.append((ws.title, rows))
        return out
    except Exception as exc:
        eprint(f"[table_tool] openpyxl failed ({exc}); using raw XML reader")
        return read_xlsx_raw(path)

def read_xlsx_raw(path):
    import xml.etree.ElementTree as ET
    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.get("Id"): r.get("Target") for r in rels}
    out = []
    for sh in wb.find(f"{NS}sheets"):
        name = sh.get("name")
        target = relmap.get(sh.get(RID), "")
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        if target not in z.namelist():
            continue
        root = ET.fromstring(z.read(target))
        rows = []
        for row in root.iter(f"{NS}row"):
            cells = []
            for c in row.findall(f"{NS}c"):
                t = c.get("t")
                v = c.find(f"{NS}v")
                if t == "s" and v is not None:
                    cells.append(shared[int(v.text)])
                elif t == "inlineStr":
                    cells.append("".join(x.text or "" for x in c.iter(f"{NS}t")))
                else:
                    cells.append(v.text if v is not None else "")
            rows.append(cells)
        out.append((name, rows))
    return out

def read_records(path):
    txt = open(path, "rb").read().decode("latin-1", "replace")
    rows = []
    keys = None
    for m in re.finditer(r"\|RECORD=[A-Za-z][^\n]*", txt):
        line = m.group(0).replace("\r", "")
        f = {k.strip(): v for k, v in re.findall(r"\|([A-Za-z0-9_ ]+)=([^|]*)", line)}
        if keys is None:
            keys = list(f.keys())
            rows.append(keys)
        rows.append([f.get(k, "") for k in keys])
    return [("records", rows)]

def load(path):
    kind = detect(path)
    if kind == "xls":
        return "xls", read_xls(path)
    if kind == "xlsx":
        return "xlsx", read_xlsx(path)
    if kind == "text-records":
        return "text-records", read_records(path)
    return "csv", read_csv(path)

def pick_sheet(sheets, want):
    if want is None:
        return sheets[0]
    if want.isdigit():
        return sheets[int(want)]
    for name, rows in sheets:
        if name == want:
            return name, rows
    raise SystemExit(f"sheet not found: {want}")

def to_csv_text(rows):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()

def main():
    ap = argparse.ArgumentParser(description="Read BOM/netlist table exports.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("read", "headers"):
        p = sub.add_parser(cmd)
        p.add_argument("file")
        p.add_argument("--sheet")
        p.add_argument("--list-sheets", action="store_true")
        p.add_argument("--json", action="store_true")
        p.add_argument("--out")
        p.set_defaults(cmd=cmd)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not os.path.isfile(args.file):
        eprint(f"[table_tool] not found: {args.file}")
        return 2
    kind, sheets = load(args.file)
    eprint(f"[table_tool] {kind}: {len(sheets)} sheet(s): " + ", ".join(n for n, _ in sheets))
    if args.list_sheets:
        for n, rows in sheets:
            print(f"{n}: {len(rows)} rows x {(len(rows[0]) if rows else 0)} cols")
        return 0

    name, rows = pick_sheet(sheets, args.sheet)
    if args.cmd == "headers":
        hdr = rows[0] if rows else []
        print(f"sheet={name} rows={len(rows)} cols={len(hdr)}")
        for i, h in enumerate(hdr):
            print(f"  [{i}] {h}")
        return 0

    text = json.dumps({"sheet": name, "rows": rows}, ensure_ascii=False, indent=2) if args.json else to_csv_text(rows)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        eprint(f"[table_tool] wrote {args.out}")
    else:
        print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
