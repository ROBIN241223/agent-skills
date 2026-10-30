# Ghi công nguồn gốc

Repo này tập hợp các agent skill từ nhiều nguồn. Bảng dưới đây ghi rõ xuất xứ từng skill. Khi một skill có file `LICENSE` riêng, file đó giữ nguyên hiệu lực và được ưu tiên hơn giấy phép ở thư mục gốc.

## Lấy từ text-to-cad (MIT, © Thompson Labs LLC)

Nguồn: <https://github.com/earthtojake/text-to-cad> — thư mục `skills/`.

| Skill | Đường dẫn gốc |
| --- | --- |
| `bambu-labs` | `skills/bambu-labs/SKILL.md` |
| `cad` | `skills/cad/SKILL.md` |
| `cad-viewer` | `skills/cad-viewer/SKILL.md` |
| `dfam-check` | `skills/dfam-check/SKILL.md` |
| `dfm` | `skills/dfm/SKILL.md` |
| `dxf` | `skills/dxf/SKILL.md` |
| `engineering-drawing` | `skills/engineering-drawing/SKILL.md` |
| `gcode` | `skills/gcode/SKILL.md` |
| `sdf` | `skills/sdf/SKILL.md` |
| `sendcutsend` | `skills/sendcutsend/SKILL.md` |
| `srdf` | `skills/srdf/SKILL.md` |
| `step-parts` | `skills/step-parts/SKILL.md` |
| `urdf` | `skills/urdf/SKILL.md` |

Mỗi thư mục skill tương ứng đều chứa bản sao `LICENSE` gốc của text-to-cad:

```
MIT License

Copyright (c) 2026 Thompson Labs LLC
```

## Lấy từ vercel-labs/skills

| Skill | Nguồn |
| --- | --- |
| `find-skills` | <https://github.com/vercel-labs/skills> — `skills/find-skills/SKILL.md` |

## Nội dung cục bộ (local)

Các skill sau được tạo hoặc tùy biến riêng cho môi trường này:

| Skill | Ghi chú |
| --- | --- |
| `altium-schematic` | Bộ công cụ đọc file Altium (`.SchDoc`, `.SchLib`, `.PcbLib`, `.IntLib`, `.PrjPcb`, `.BomDoc`) và quy trình review mạch |
| `doc-research` | Quy trình đọc tài liệu + nghiên cứu web có trích dẫn |
| `read-documents` | Trích xuất văn bản/bảng từ ảnh, PDF, Word, Excel, PowerPoint |
| `vinacad` | Tự động hóa VinaCAD/IntelliCAD trên Windows và xuất DWG |
| `tra-loi-tieng-viet` | Ràng buộc ngôn ngữ trả lời tiếng Việt |

## Giấy phép repo

Phần nội dung do repo này tạo (README, `ATTRIBUTION.md`, `scripts/install.*`) phát hành theo MIT — xem [LICENSE](LICENSE). Giấy phép này không áp đặt lên các skill của bên thứ ba; các skill đó vẫn chịu giấy phép gốc của chúng.

Nếu bạn là tác giả và muốn nội dung của mình được gỡ bỏ hoặc ghi công khác, hãy mở issue trong repo.
