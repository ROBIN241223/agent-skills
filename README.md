# OpenCode Skills Collection

Bộ sưu tập 19 **agent skills** đang dùng trong OpenCode, đóng gói lại thành một repo độc lập để dễ chia sẻ, cài đặt và tái sử dụng.

Mỗi skill là một thư mục chứa `SKILL.md` (mô tả + hướng dẫn cho agent) cùng các tài liệu tham chiếu và script đi kèm. Agent sẽ tự nạp skill khi tác vụ khớp với phần `description`.

## Danh mục skills

| Skill | Chức năng | Nguồn |
| --- | --- | --- |
| `cad` | Tạo/sửa mô hình CAD tham số, quản lý project, xuất STEP/STL/3MF/GLB, đo hình học bằng `cadgen` | text-to-cad |
| `cad-viewer` | Khởi động CAD Viewer, trả link review cho `.step` `.stl` `.3mf` `.glb` `.dxf` `.urdf` `.srdf` `.sdf` | text-to-cad |
| `dfam-check` | Đánh giá mesh theo quy tắc DfAM (FDM, SLS, SLA/DLP, metal PBF, MJF): overhang, thành mỏng, hướng in | text-to-cad |
| `dfm` | Review thiết kế cho gia công: sheet metal (bend, relief, flat pattern), CNC (gá, góc trong), ép nhựa (draft, undercut) | text-to-cad |
| `dxf` | Sinh và kiểm tra bản vẽ 2D DXF từ source Python `build123d` | text-to-cad |
| `engineering-drawing` | Xuất bản vẽ kỹ thuật PDF: hình chiếu, hidden line, dimension, title block theo ISO | text-to-cad |
| `gcode` | Sinh, kiểm tra, dry-run G-code FDM qua các slicer CLI; đánh giá mesh có sẵn sàng slice | text-to-cad |
| `bambu-labs` | Dry-run, upload và chạy lệnh in Bambu Lab qua LAN (FTPS/MQTT) | text-to-cad |
| `step-parts` | Tìm và tải chi tiết CAD có sẵn (động cơ, servo, ốc, vòng bi...) từ step.parts | text-to-cad |
| `sendcutsend` | Preflight DXF/STEP cho đơn hàng SendCutSend: vật liệu, độ dày, dịch vụ, khả năng upload | text-to-cad |
| `urdf` | Viết, sửa, kiểm tra URDF: link, joint, limit, inertial, mesh, frame | text-to-cad |
| `srdf` | Viết, sửa, kiểm tra MoveIt2 SRDF: planning group, end effector, disabled collision | text-to-cad |
| `sdf` | Viết, kiểm tra SDFormat/Gazebo: model, world, sensor, physics, plugin | text-to-cad |
| `altium-schematic` | Đọc file Altium (`.SchDoc` `.SchLib` `.PcbLib` `.IntLib` `.PrjPcb` `.BomDoc`), trích linh kiện/net, review mạch và độ ổn định vòng điều khiển | local |
| `doc-research` | Đọc ảnh/PDF (OCR, bảng, metadata) rồi nghiên cứu sâu bằng web search, tổng hợp có trích dẫn | local |
| `read-documents` | Chuyển tài liệu (ảnh, PDF, Word, Excel, PowerPoint, CSV/HTML/JSON) thành text/Markdown | local |
| `vinacad` | Điều khiển VinaCAD/IntelliCAD trên Windows bằng phím lệnh, xử lý hộp thoại Recovery, xuất `.dwg` | local |
| `tra-loi-tieng-viet` | Ràng buộc agent luôn trả lời bằng tiếng Việt, giữ văn phong mạch lạc | local |
| `find-skills` | Khám phá và cài thêm skill khi thiếu năng lực | vercel-labs/skills |

## Cấu trúc repo

```
opencode-skills/
├── README.md
├── ATTRIBUTION.md
├── LICENSE
├── .gitignore
├── .github/workflows/validate.yml
├── skills/
│   ├── cad/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/*.md
│   │   ├── requirements.txt
│   │   └── LICENSE
│   ├── urdf/
│   └── ...
└── scripts/
    ├── install.ps1
    ├── install.sh
    └── validate_skills.py
```

Mỗi skill giữ nguyên cấu trúc gốc:

- `SKILL.md` — frontmatter (`name`, `description`) và hướng dẫn thực thi.
- `agents/openai.yaml` — metadata cho agent.
- `references/` — tài liệu chuyên sâu được nạp khi cần.
- `scripts/` — công cụ Python/PowerShell hỗ trợ.
- `requirements.txt` — thư viện Python cần cho skill đó.

## Cài đặt

### Windows (PowerShell)

```powershell
git clone https://github.com/ROBIN241223/opencode-skills.git
cd opencode-skills

# Cài vào thư mục skill dùng chung cho mọi agent (~/.agents/skills)
.\scripts\install.ps1

# Hoặc chỉ định thư mục đích
.\scripts\install.ps1 -Target "$env:USERPROFILE\.config\opencode\skills"

# Nếu máy không cho tạo symlink, dùng chế độ copy
.\scripts\install.ps1 -Copy
```

### Linux / macOS

```bash
git clone https://github.com/ROBIN241223/opencode-skills.git
cd opencode-skills
./scripts/install.sh                       # mặc định: ~/.agents/skills
./scripts/install.sh ~/.config/opencode/skills
./scripts/install.sh --copy ~/.claude/skills
```

Script sẽ tạo symlink cho từng skill (khuyến nghị, để `git pull` là cập nhật ngay), và tự chuyển sang copy nếu hệ thống không hỗ trợ.

### Cài thủ công

Chỉ cần copy thư mục skill vào nơi agent quét skill:

- OpenCode: `~/.config/opencode/skills/`
- Claude Code: `~/.claude/skills/`
- Dùng chung: `~/.agents/skills/`

## Cài thư viện Python

Một số skill cần thêm package (CAD, DXF, xử lý tài liệu...):

```bash
pip install -r skills/cad/requirements.txt
pip install -r skills/dxf/requirements.txt
pip install -r skills/dfm/requirements.txt
```

Hoặc cài toàn bộ:

```powershell
Get-ChildItem skills\*\requirements.txt | ForEach-Object { pip install -r $_.FullName }
```

```bash
find skills -name requirements.txt -exec pip install -r {} \;
```

## Cách dùng

Sau khi cài, không cần gọi tên skill. Agent tự so khớp `description` với yêu cầu, ví dụ:

- "Xuất bản vẽ kỹ thuật PDF cho chi tiết này" → `engineering-drawing`
- "Chi tiết này in FDM được không?" → `dfam-check`
- "Kiểm tra file URDF này" → `urdf`
- "Đọc PDF này rồi tóm tắt" → `read-documents` / `doc-research`
- "Xuất bản vẽ sang DWG" → `vinacad`

Một số môi trường cho phép gọi trực tiếp bằng cú pháp `$skill-name` (ví dụ `$cad`, `$gcode`).

## Yêu cầu môi trường

- Windows 10/11, Linux hoặc macOS.
- Python 3.10+ cho các skill có `scripts/*.py`.
- Các skill CAD/G-code cần công cụ ngoài (FreeCAD/build123d, slicer CLI, CAD Viewer) — xem `references/` của từng skill.
- `vinacad` và các script `.ps1` chỉ chạy trên Windows.

## Bản quyền và ghi công

- 13 skill lấy từ [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) — MIT, © Thompson Labs LLC.
- `find-skills` lấy từ [vercel-labs/skills](https://github.com/vercel-labs/skills).
- 5 skill còn lại (`altium-schematic`, `doc-research`, `read-documents`, `vinacad`, `tra-loi-tieng-viet`) do chủ repo tạo hoặc tùy biến.

Mỗi skill giữ nguyên file `LICENSE` gốc. Chi tiết xem [ATTRIBUTION.md](ATTRIBUTION.md). Giấy phép MIT ở thư mục gốc chỉ áp dụng cho phần nội dung của repo này (README, script cài đặt) và **không** thay thế giấy phép của từng skill.

## Đóng góp

Mở issue hoặc pull request. Khi thêm skill mới, giữ cấu trúc `skills/<ten-skill>/SKILL.md` với frontmatter `name` và `description` rõ ràng, kèm nguồn gốc trong `ATTRIBUTION.md`.

Trước khi commit, chạy kiểm tra:

```bash
python scripts/validate_skills.py
```

Workflow `.github/workflows/validate.yml` chạy bước này tự động trên mỗi lần push và pull request.
