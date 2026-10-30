#!/usr/bin/env python3
"""Read Altium Designer files (schematic, libraries, projects, BOM docs).

Tested against real Altium 24 files: binary .SchDoc/.SchLib/.PcbLib (OLE2 compound
files containing pipe-delimited `|RECORD=...` ASCII records), compiled .IntLib
(zlib-wrapped OLE2), text .PrjPcb/.OutJob (INI), and text .BomDoc.

Subcommands:
  info FILE...                 detect kind, header, streams, record histogram
  project FILE.PrjPcb          parse project text: documents, libraries, settings
  schematic FILE.SchDoc        components, params, footprints, named nets
  lib FILE.{SchLib,PcbLib,IntLib}  symbols / footprints in a library
  bom  FILE.SchDoc...          aggregate a BOM across sheets -> CSV/JSON
  bomdoc FILE.BomDoc           parse Altium LiveBOM CatalogItem records
  records FILE [--type N]      dump raw records (debugging/undocumented types)

Needs: olefile (pip install olefile). Everything else is stdlib.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import zlib

try:
    import olefile
except Exception:  # pragma: no cover
    olefile = None

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# Altium schematic/PCB record type names (best-known subset)
REC = {
    1: "Component", 2: "Pin", 3: "IEEE", 4: "NetLabel", 5: "Bezier", 6: "Polyline",
    7: "Polygon", 8: "Ellipse", 9: "Arc", 10: "Line", 11: "Port", 12: "Text",
    13: "Rectangle", 14: "Rectangle", 15: "Annotation", 16: "Noserc", 17: "PowerPort",
    18: "Port", 22: "NoERC", 25: "NetLabel", 27: "Wire", 28: "Bus", 29: "Junction",
    30: "BusEntry", 31: "Sheet", 34: "Designator", 41: "Parameter", 44: "ImplementationList",
    45: "Implementation", 46: "ImplementationMap", 48: "Implementation",
}

def eprint(*a):
    print(*a, file=sys.stderr)

def read_head(path, n=16):
    with open(path, "rb") as fh:
        return fh.read(n)

def sniff(path):
    head = read_head(path, 32)
    if head.startswith(OLE_MAGIC):
        return "ole"
    if head.startswith(b"\xef\xbb\xbf["):
        return "ini"
    if head[:1] == b"[":
        return "ini"
    if head.startswith(b"|RECORD="):
        return "records-text"
    if head.startswith(b"\x02\x78\x9c"):
        return "intlib-stream"
    return "unknown"

# --------------------------------------------------------------- record plumbing
def consume(data, deep, out, max_bytes):
    """Recursively collect raw record blobs from raw/compressed/OLE bytes."""
    if data is None:
        return
    if data.startswith(OLE_MAGIC):
        if olefile is None:
            raise RuntimeError("olefile not installed: pip install olefile")
        try:
            sub = olefile.OleFileIO(io.BytesIO(data))
        except Exception:
            return
        for s in sub.listdir():
            try:
                piece = sub.openstream(s).read()
            except Exception:
                continue
            consume(piece, deep, out, max_bytes)
        return
    if len(data) > 3 and data[0] in (0x00, 0x01, 0x02, 0x03) and data[1:3] == b"\x78\x9c":
        try:
            consume(zlib.decompress(data[1:]), deep, out, max_bytes)
            return
        except Exception:
            pass
    if b"|RECORD=" in data or b"|HEADER=" in data:
        if max_bytes and len(data) > max_bytes:
            eprint(f"[altium] note: large stream ({len(data)} bytes) truncated to {max_bytes}")
            data = data[:max_bytes]
        out.append(data)

def collect(path, deep=True, max_bytes=0):
    out = []
    if sniff(path) == "ole":
        if olefile is None:
            raise RuntimeError("olefile not installed: pip install olefile")
        ole = olefile.OleFileIO(path)
        for s in ole.listdir():
            try:
                consume(ole.openstream(s).read(), deep, out, max_bytes)
            except Exception:
                continue
    else:
        consume(open(path, "rb").read(), deep, out, max_bytes)
    return out

def parse_header(blobs):
    header = {}
    for b in blobs:
        m = re.search(rb"\|HEADER=([^|\x00]*)", b)
        if m:
            txt = m.group(1).decode("latin-1", "replace")
            header["HEADER"] = txt
            for k, v in re.findall(r"([A-Za-z0-9_]+)=([^|\x00]*)", txt):
                header.setdefault(k, v)
            break
    return header

def parse_records(blobs):
    recs = []
    for b in blobs:
        for p in re.split(rb"(?=\|RECORD=)", b):
            if not p.startswith(b"|RECORD="):
                continue
            cut = p.split(b"\x00", 1)[0]
            recs.append(cut.decode("latin-1", "replace"))
    return recs

def fields(raw):
    m = re.match(r"\|RECORD=(\d+)", raw)
    t = int(m.group(1)) if m else None
    d = {k: v for k, v in re.findall(r"\|([A-Za-z0-9_.% ]+)=([^|]*)", raw)}
    d["__type"] = t
    d["__raw"] = raw
    return d

# --------------------------------------------------------------- schematic
def components(recs):
    parsed = [fields(r) for r in recs]
    comps = {}
    impl_owner = {}  # RECORD=44 (implementation list) index -> component index
    for i, f in enumerate(parsed):
        if f["__type"] == 1:
            comps[i] = {
                "index": i,
                "libref": f.get("LibReference") or f.get("Name"),
                "description": f.get("ComponentDescription"),
                "partcount": f.get("PartCount"),
                "designator": None,
                "footprint": None,
                "params": {},
                "pins": [],
            }
        elif f["__type"] == 44:
            oi = f.get("OwnerIndex")
            if oi and oi.isdigit() and int(oi) in comps:
                impl_owner[i] = int(oi)
    for i, f in enumerate(parsed):
        oi = f.get("OwnerIndex")
        if not (oi and oi.isdigit()):
            continue
        o = int(oi)
        t = f["__type"]
        if t == 34 and o in comps:
            comps[o]["designator"] = f.get("Text")
        elif t == 2 and o in comps:
            comps[o]["pins"].append({
                "name": f.get("Name"),
                "number": f.get("Designator"),
                "electrical": f.get("Electrical"),
            })
        elif t == 41 and f.get("Name") and o in comps:
            # keep the first (visible) value; don't let later duplicates overwrite
            comps[o]["params"].setdefault(f["Name"], f.get("Text"))
        elif t == 45 and (f.get("ModelType") or "").upper() == "PCBLIB":
            comp = impl_owner.get(o)  # 45 -> 44 -> component
            model = f.get("ModelName")
            if comp is not None and model:
                if not comps[comp]["footprint"] or f.get("IsCurrent") == "T":
                    comps[comp]["footprint"] = model
    return list(comps.values())

def named_nets(recs):
    nets = {"labels": [], "power": [], "ports": []}
    for r in recs:
        f = fields(r)
        if f["__type"] == 4 and f.get("Text"):
            nets["labels"].append(f["Text"])
        elif f["__type"] == 17 and f.get("Text"):
            nets["power"].append(f["Text"])
        elif f["__type"] == 18 and f.get("Name"):
            nets["ports"].append(f["Name"])
    for k in nets:
        nets[k] = sorted(set(nets[k]))
    return nets

def comp_row(c):
    p = c["params"]
    return {
        "designator": c["designator"] or "",
        "libref": c["libref"] or "",
        "value": p.get("Value") or p.get("Comment") or "",
        "footprint": c["footprint"] or p.get("Footprint") or "",
        "manufacturer": p.get("Manufacturer") or p.get("MF") or p.get("Manufacturer 1") or "",
        "mpn": p.get("Manufacturer Part Number") or p.get("Manufacturer_Part_Number")
               or p.get("MPN") or p.get("MP") or "",
        "description": c["description"] or p.get("Description") or "",
        "pins": len(c["pins"]),
        "partcount": c["partcount"] or "",
    }

# --------------------------------------------------------------- project (INI)
def read_ini(path):
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", "replace")
    sections = {}
    cur = None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("[") and s.endswith("]"):
            cur = s[1:-1]
            sections.setdefault(cur, [])
        elif cur is not None and "=" in s:
            k, _, v = s.partition("=")
            sections[cur].append((k.strip(), v.strip()))
    return sections

def project_info(path):
    sec = read_ini(path)
    docs = []
    for name, kvs in sec.items():
        if not name.lower().startswith("document"):
            continue
        d = dict(kvs)
        fn = d.get("DocumentPath") or d.get("FileName")
        if not fn:
            continue
        docs.append({
            "section": name,
            "filename": fn,
            "kind": os.path.splitext(fn)[1].lower().lstrip("."),
            "unique_id": d.get("DocumentUniqueId", ""),
        })
    lib_exts = {"schlib", "pcblib", "intlib"}
    return {"sections": sec,
            "documents": [d for d in docs if d["kind"] not in lib_exts],
            "libraries": [d for d in docs if d["kind"] in lib_exts],
            "design": dict(sec.get("Design", []))}

# --------------------------------------------------------------- bomdoc
def bomdoc_items(path):
    txt = open(path, "rb").read().decode("latin-1", "replace")
    items = []
    for m in re.finditer(r"\|RECORD=CatalogItem\|[^\n]*", txt):
        line = m.group(0).replace("\r", "")
        f = {k.strip(): v for k, v in re.findall(r"\|([A-Za-z0-9_ ]+)=([^|]*)", line)}
        params = {}
        cp = f.get("COMPONENTPARAMETERS", "")
        for pm in re.finditer(r'"([^"]+?)"', cp):
            inner = pm.group(1)
            if "=" in inner:
                k, _, v = inner.partition("=")
                params[k.strip()] = v.strip()
        part = (params.get("Manufacturer Part Number") or params.get("MP")
                or f.get("USERCOMMENTS") or f.get("DESIGNITEMID") or "")
        items.append({
            "design_item": f.get("DESIGNITEMID", ""),
            "source": f.get("ITEMSOURCE", ""),
            "status": f.get("STATUS", ""),
            "description": f.get("DESCRIPTION", ""),
            "comment": f.get("USERCOMMENTS", ""),
            "params": params,
            "manufacturer": params.get("Manufacturer", "") or params.get("MF", ""),
            "mpn": part,
            "footprint": params.get("Footprint", "") or params.get("Package", ""),
            "datasheet": params.get("Datasheet Link", "") or params.get("Datasheet", ""),
        })
    return items

# --------------------------------------------------------------- output helpers
def out_write(text, out):
    if out:
        with open(out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        eprint(f"[altium] wrote {len(text)} chars to {out}")
    else:
        print(text)

def as_csv(rows, out):
    if not rows:
        out_write("(no rows)", out)
        return
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    out_write(buf.getvalue(), out)

# --------------------------------------------------------------- commands
def cmd_info(args):
    for path in args.files:
        print("=" * 72)
        print(path)
        kind = sniff(path)
        ext = os.path.splitext(path)[1].lower()
        print(f"  sniff={kind} ext={ext} size={os.path.getsize(path)}")
        if kind == "ole":
            ole = olefile.OleFileIO(path)
            for s in ole.listdir():
                print(f"    stream {'/'.join(s):50} {ole.get_size(s)}")
        try:
            blobs = collect(path, max_bytes=args.max_bytes)
            header = parse_header(blobs)
            recs = parse_records(blobs)
            if header:
                print("  header:", header.get("HEADER", "")[:120])
            import collections
            hist = collections.Counter(fields(r)["__type"] for r in recs)
            pretty = {REC.get(k, str(k)): v for k, v in sorted(hist.items(), key=lambda x: (x[0] is None, x[0]))}
            print(f"  records={len(recs)} types={pretty}")
        except Exception as exc:
            print("  record scan failed:", exc)

def cmd_project(args):
    info = project_info(args.file)
    print(f"Project: {os.path.basename(args.file)}")
    print(f"Documents ({len(info['documents'])}):")
    for d in info["documents"]:
        print(f"  - {d['filename']}  [{d['kind']}]")
    if info["libraries"]:
        print(f"Libraries ({len(info['libraries'])}):")
        for l in info["libraries"]:
            print(f"  - {l['filename']}")
    print("Design settings:")
    for k, v in info["design"].items():
        print(f"  {k} = {v}")
    if args.json:
        out_write(json.dumps(info, indent=2, ensure_ascii=False), args.out)

def cmd_schematic(args):
    blobs = collect(args.file)
    recs = parse_records(blobs)
    comps = [comp_row(c) for c in components(recs)]
    nets = named_nets(recs)
    if args.json:
        out_write(json.dumps({"components": comps, "nets": nets}, indent=2, ensure_ascii=False), args.out)
        return
    print(f"# {os.path.basename(args.file)}  ({len(comps)} components)")
    print(f"{'Designator':<14}{'LibRef':<26}{'Value':<20}{'Footprint':<22}MPN")
    for c in sorted(comps, key=lambda x: (x["designator"] or "zzz")):
        print(f"{c['designator']:<14}{c['libref'][:24]:<26}{c['value'][:18]:<20}{c['footprint'][:20]:<22}{c['mpn']}")
    if args.nets:
        print("\nNamed nets:")
        print("  labels:", ", ".join(nets["labels"]) or "(none)")
        print("  power :", ", ".join(nets["power"]) or "(none)")
        print("  ports :", ", ".join(nets["ports"]) or "(none)")
    if args.out:
        as_csv(comps, args.out)

PCB_INFRA = {"FileHeader", "FileVersionInfo", "Library", "Textures", "EmbeddedFonts",
             "Models", "ModelsNoEmbed", "PadViaLibrary", "PrimitiveGuids",
             "UniqueIDPrimitiveInformation", "WideStrings", "ComponentParamsTOC",
             "LayerKindMapping"}

def pcb_footprint_names(path):
    names = set()

    def scan(ole):
        for s in ole.listdir():
            if s and s[0] not in PCB_INFRA:
                names.add(s[0])

    if sniff(path) == "ole":
        ole = olefile.OleFileIO(path)
        top = ["/".join(s) for s in ole.listdir()]
        embedded = [n for n in top if n.endswith(".pcblib")]
        if embedded:
            for n in embedded:
                try:
                    dec = zlib.decompress(ole.openstream(n).read()[1:])
                    scan(olefile.OleFileIO(io.BytesIO(dec)))
                except Exception:
                    pass
        else:
            scan(ole)
    return sorted(names)

def cmd_lib(args):
    ext = os.path.splitext(args.file)[1].lower()
    blobs = collect(args.file)
    recs = parse_records(blobs)
    header = parse_header(blobs)
    comps = [comp_row(c) for c in components(recs)]

    if ext == ".pcblib" or (not comps and sniff(args.file) == "ole"):
        names = pcb_footprint_names(args.file)
        print(f"# {os.path.basename(args.file)} (footprint library), {len(names)} footprints")
        for n in names:
            print("  ", n)
        if args.json:
            out_write(json.dumps({"footprints": names}, indent=2, ensure_ascii=False), args.out)
        return

    print(f"# {os.path.basename(args.file)}  ({len(comps)} symbols)")
    if ext == ".intlib":
        fps = pcb_footprint_names(args.file)
        if fps:
            print(f"# embedded footprints ({len(fps)}): " + ", ".join(fps[:20]))
    if header.get("CompCount"):
        print("header CompCount =", header.get("CompCount"))
    for c in comps:
        print(f"  {c['libref']:<30} parts={c['partcount']:<3} pins={c['pins']:<3} fp={c['footprint']}")
        if c["description"]:
            print(f"      {c['description'][:110]}")
    if args.json:
        out_write(json.dumps(comps, indent=2, ensure_ascii=False), args.out)

def _designator_base(d):
    return re.sub(r"[A-Za-z]$", "", d) if re.search(r"[A-Za-z]{1,2}\d+[A-Za-z]?$", d or "") else (d or "")

def cmd_bom(args):
    rows = {}
    for path in args.files:
        recs = parse_records(collect(path))
        for c in components(recs):
            r = comp_row(c)
            key = (r["libref"], r["value"], r["footprint"])
            row = rows.setdefault(key, {"libref": r["libref"], "value": r["value"],
                                        "footprint": r["footprint"], "mpn": r["mpn"],
                                        "manufacturer": r["manufacturer"],
                                        "description": r["description"], "designators": set()})
            if r["designator"]:
                row["designators"].add(r["designator"])
    out_rows = []
    for row in rows.values():
        row["qty"] = len(row["designators"])
        row["designators"] = ", ".join(sorted(row["designators"]))
        out_rows.append(row)
    out_rows.sort(key=lambda x: x["designators"])
    as_csv(out_rows, args.out)
    eprint(f"[altium] {len(out_rows)} BOM lines from {len(args.files)} sheet(s)")

def cmd_bomdoc(args):
    items = bomdoc_items(args.file)
    if args.json:
        out_write(json.dumps(items, indent=2, ensure_ascii=False), args.out)
        return
    rows = [{"design_item": i["design_item"], "mpn": i["mpn"], "manufacturer": i["manufacturer"],
             "footprint": i["footprint"], "status": i["status"], "source": i["source"],
             "description": i["description"], "datasheet": i["datasheet"]} for i in items]
    as_csv(rows, args.out)

def cmd_records(args):
    recs = parse_records(collect(args.file))
    if args.type is not None:
        recs = [r for r in recs if fields(r)["__type"] == args.type]
    if args.raw:
        out_write("\n".join(recs), args.out)
        return
    for r in recs:
        f = fields(r)
        f.pop("__raw", None)
        print(json.dumps(f, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser(description="Read Altium Designer files.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info"); p.add_argument("files", nargs="+"); p.add_argument("--max-bytes", type=int, default=0); p.set_defaults(func=cmd_info)
    p = sub.add_parser("project"); p.add_argument("file"); p.add_argument("--json", action="store_true"); p.add_argument("--out"); p.set_defaults(func=cmd_project)
    p = sub.add_parser("schematic"); p.add_argument("file"); p.add_argument("--json", action="store_true"); p.add_argument("--nets", action="store_true"); p.add_argument("--out"); p.set_defaults(func=cmd_schematic)
    p = sub.add_parser("lib"); p.add_argument("file"); p.add_argument("--json", action="store_true"); p.add_argument("--out"); p.set_defaults(func=cmd_lib)
    p = sub.add_parser("bom"); p.add_argument("files", nargs="+"); p.add_argument("--out"); p.set_defaults(func=cmd_bom)
    p = sub.add_parser("bomdoc"); p.add_argument("file"); p.add_argument("--json", action="store_true"); p.add_argument("--out"); p.set_defaults(func=cmd_bomdoc)
    p = sub.add_parser("records"); p.add_argument("file"); p.add_argument("--type", type=int); p.add_argument("--raw", action="store_true"); p.add_argument("--out"); p.set_defaults(func=cmd_records)

    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return args.func(args) or 0

if __name__ == "__main__":
    raise SystemExit(main())
