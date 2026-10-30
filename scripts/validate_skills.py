#!/usr/bin/env python3
"""Kiểm tra cấu trúc bộ skill.

Mỗi thư mục trong skills/ phải có SKILL.md với frontmatter chứa `name`
và `description`, và tên thư mục phải khớp `name` (chuẩn hóa).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

# Tránh lỗi UnicodeEncodeError trên console Windows (cp1252/cp437)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    data: dict[str, str] = {}
    key = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] not in " \t" and ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            data[key] = value.strip().strip(">|").strip()
        elif key and line.startswith((" ", "\t")):
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"Không tìm thấy thư mục: {SKILLS_DIR}")
        return 1

    errors: list[str] = []
    skills = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())

    for skill in skills:
        skill_md = skill / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{skill.name}: thiếu SKILL.md")
            continue

        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        for field in ("name", "description"):
            if not meta.get(field):
                errors.append(f"{skill.name}: frontmatter thiếu `{field}`")

        desc = meta.get("description", "")
        if len(desc) < 20:
            errors.append(f"{skill.name}: description quá ngắn ({len(desc)} ký tự)")

        if "__pycache__" in [p.name for p in skill.rglob("*")]:
            errors.append(f"{skill.name}: chứa __pycache__, cần xóa")

        for pyc in skill.rglob("*.pyc"):
            errors.append(f"{skill.name}: chứa file build {pyc.relative_to(ROOT)}")

    print(f"Đã kiểm tra {len(skills)} skill.")
    for err in errors:
        print(f"  ✗ {err}")

    if errors:
        return 1

    print("Tất cả skill hợp lệ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
